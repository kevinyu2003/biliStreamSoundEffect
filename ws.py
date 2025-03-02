import asyncio
import json
import websockets
import requests
import time
import hashlib
import hmac
import random
from hashlib import sha256
import proto
import urllib3
import os
import numpy as np
import sounddevice as sd
import soundfile as sf
from threading import Lock
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
#此代码在python样本上由莫比乌斯余XD进行修改
CONFIG_FILE = 'config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'idCode': '',
        'soundMappings': {
            'likeSound': 'Waga.wav',
            'giftSound1': 'Ouye.wav',
            'giftSound2': 'Hachimi.wav',
            'giftSound3': 'Wow.wav',
            'messageSound': 'Manbo.wav'
        }
    }

class SoundManager:
    def __init__(self):
        # Audio system attributes
        self.stream_lock = Lock()
        self.active_sounds = {}
        self.output_stream = None
        self.sample_rate = 44100  # Default sample rate
        
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Load configuration
        self.config = load_config()
        self.reload_config()

    def reload_config(self):
        """Reload configuration and update settings"""
        self.config = load_config()
        sound_mappings = self.config['soundMappings']
        self.volume_settings = self.config.get('volumeSettings', {})
        
        # Audio file mappings with absolute paths
        self.audio_files = {}
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        for key, files in sound_mappings.items():
            event_key = key.replace('Sound', '').lower()
            if isinstance(files, list):
                self.audio_files[event_key] = []
                for f in files:
                    file_path = os.path.join(script_dir, 'sound', f)
                    if os.path.exists(file_path):
                        self.audio_files[event_key].append(file_path)
            else:
                # Handle legacy config format
                file_path = os.path.join(script_dir, 'sound', files)
                if os.path.exists(file_path):
                    self.audio_files[event_key] = [file_path]
                else:
                    self.audio_files[event_key] = []

        # Load audio files
        self.audio_data = {}
        self._load_audio_files()
        self._initialize_output_stream()
    
    def _load_audio_files(self):
        """Load all audio files into memory and resample if needed"""
        for key, file_paths in self.audio_files.items():
            self.audio_data[key] = []
            if not file_paths:
                print(f"[音频管理] 警告: 没有为 {key} 配置音效喵！没配置也能使用，只是告诉你一下喵！")
                continue
                
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    print(f"[音频管理] 错误: 音频找不到喵！: {file_path}")
                    continue
                    
                try:
                    data, fs = sf.read(file_path)
                    if data is None or len(data) == 0:
                        print(f"[音频管理] 错误：{file_path} 没有指定音频或者音频格式不对喵！")
                        continue
                        
                    # Convert to mono if stereo
                    if len(data.shape) > 1:
                        data = np.mean(data, axis=1)
                        
                    # Resample if different from target sample rate
                    if fs != self.sample_rate:
                        try:
                            samples = int(len(data) * self.sample_rate / fs)
                            data = np.interp(
                                np.linspace(0, len(data), samples, endpoint=False),
                                np.arange(len(data)),
                                data
                            )
                        except Exception as e:
                            print(f"[SoundManager] Error resampling {file_path}: {e}")
                            continue
                            
                    self.audio_data[key].append(data)
                    print(f"[音效管理器] 成功加载: {file_path}")
                except Exception as e:
                    print(f"[音效管理器] 加载音频文件失败 {file_path}: {e}")
                    continue
    
    def _initialize_output_stream(self):
        """Initialize the single output stream for mixing"""
        try:
            self.output_stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                callback=self._mix_callback,
                blocksize=1024
            )
            self.output_stream.start()
        except Exception as e:
            print(f"初始化输出流时发生错误: {e}")

    def play_audio(self, key, volume=1):
        """Play an audio file with the specified key and volume"""
        if key not in self.audio_data or not self.audio_data[key]:
            # Just log a debug message and return silently
            print(f"[音效管理器] 未配置该事件的音效: {key}")
            return

        with self.stream_lock:
            # Randomly select one of the available sounds for this event
            selected_sound = random.choice(self.audio_data[key])
            sound_id = str(time.time())
            
            # Get the filename for this sound type
            sound_key = key + 'Sound'  # Convert 'like' to 'likeSound' etc.
            if sound_key in self.config['soundMappings']:
                # Get the filename of the selected sound
                sound_files = self.config['soundMappings'][sound_key]
                if sound_files:
                    # Find the original filename that matches our selected sound data
                    for filename in sound_files:
                        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sound', filename)
                        try:
                            data, _ = sf.read(file_path)
                            if len(data.shape) > 1:
                                data = np.mean(data, axis=1)
                            if np.array_equal(data, selected_sound):
                                # Get volume setting for this file (0-100) and convert to float (0-1)
                                file_volume = self.volume_settings.get(filename, 100) / 100.0
                                volume = volume * file_volume
                                break
                        except Exception:
                            continue
            
            self.active_sounds[sound_id] = {
                'data': selected_sound * volume,
                'position': 0
            }
    
    def _mix_callback(self, outdata, frames, time, status):
        """Mix active sounds and write to output buffer"""
        if status:
            print(status)

        with self.stream_lock:
            # Initialize output buffer
            mixed_data = np.zeros(frames)

            # Mix all active sounds
            finished_sounds = []
            for sound_id, sound in self.active_sounds.items():
                remaining = len(sound['data']) - sound['position']
                if remaining <= 0:
                    finished_sounds.append(sound_id)
                    continue

                # Calculate how many samples to mix
                n_samples = min(frames, remaining)
                mixed_data[:n_samples] += sound['data'][sound['position']:sound['position'] + n_samples]
                sound['position'] += n_samples

                if sound['position'] >= len(sound['data']):
                    finished_sounds.append(sound_id)

            # Remove finished sounds
            for sound_id in finished_sounds:
                self.active_sounds.pop(sound_id)

            # Normalize mixed data to prevent clipping
            if len(self.active_sounds) > 0:
                max_val = np.max(np.abs(mixed_data))
                if max_val > 1.0:
                    mixed_data /= max_val

            # Write to output buffer
            outdata[:, 0] = mixed_data


class BiliClient:
    def __init__(self, idCode, appId, key, secret, host):
        self.idCode = idCode
        self.appId = appId
        self.key = key
        self.secret = secret
        self.host = host
        self.gameId = ''
        self.config = load_config()  # Load configuration during initialization
        self.sound_manager = SoundManager()
        pass

    # 事件循环
    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # 建立连接
        websocket = loop.run_until_complete(self.connect())
        tasks = [
            # 读取信息
            asyncio.ensure_future(self.recvLoop(websocket)),
            # 发送心跳
            asyncio.ensure_future(self.heartBeat(websocket)),
             # 发送游戏心跳
            asyncio.ensure_future(self.appheartBeat()),
        ]
        loop.run_until_complete(asyncio.gather(*tasks))

    # http的签名
    def sign(self, params):
        key = self.key
        secret = self.secret
        md5 = hashlib.md5()
        md5.update(params.encode())
        ts = time.time()
        nonce = random.randint(1, 100000)+time.time()
        md5data = md5.hexdigest()
        headerMap = {
            "x-bili-timestamp": str(int(ts)),
            "x-bili-signature-method": "HMAC-SHA256",
            "x-bili-signature-nonce": str(nonce),
            "x-bili-accesskeyid": key,
            "x-bili-signature-version": "1.0",
            "x-bili-content-md5": md5data,
        }

        headerList = sorted(headerMap)
        headerStr = ''

        for key in headerList:
            headerStr = headerStr + key+":"+str(headerMap[key])+"\n"
        headerStr = headerStr.rstrip("\n")

        appsecret = secret.encode()
        data = headerStr.encode()
        signature = hmac.new(appsecret, data, digestmod=sha256).hexdigest()
        headerMap["Authorization"] = signature
        headerMap["Content-Type"] = "application/json"
        headerMap["Accept"] = "application/json"
        return headerMap

    # 获取长连信息
    def getWebsocketInfo(self):
        # 开启应用
        postUrl = "%s/v2/app/start" % self.host
        params = '{"code":"%s","app_id":%d}' % (self.idCode, self.appId)
        headerMap = self.sign(params)
        r = requests.post(url=postUrl, headers=headerMap,
                          data=params, verify=False)
        data = json.loads(r.content)

        self.gameId = str(data['data']['game_info']['game_id'])

        # 获取长连地址和鉴权体
        return str(data['data']['websocket_info']['wss_link'][0]), str(data['data']['websocket_info']['auth_body'])

     # 发送游戏心跳
    async def appheartBeat(self):
        while True:
            await asyncio.ensure_future(asyncio.sleep(20))
            postUrl = "%s/v2/app/heartbeat" % self.host
            params = '{"game_id":"%s"}' % (self.gameId)
            headerMap = self.sign(params)
            r = requests.post(url=postUrl, headers=headerMap,
                          data=params, verify=False)
            data = json.loads(r.content)
            print("[音效姬] 心跳发送成功喵~！")

    # 发送鉴权信息
    async def auth(self, websocket, authBody):
        req = proto.Proto()
        req.body = authBody
        req.op = 7
        await websocket.send(req.pack())
        buf = await websocket.recv()
        resp = proto.Proto()
        resp.unpack(buf)
        respBody = json.loads(resp.body)
        if respBody["code"] != 0:
            print("认证失败喵~！")
        else:
            print("认证成功喵~！")
            print("音效姬由莫比乌斯余XD调教制作,有问题可以去bilibili私信莫比乌斯余XD喵~！")

    # 发送心跳
    async def heartBeat(self, websocket):
        while True:
            await asyncio.ensure_future(asyncio.sleep(20))
            req = proto.Proto()
            req.op = 2
            await websocket.send(req.pack())
            print("[音效姬] 发送心跳成功喵~！")

    # 读取信息
    async def recvLoop(self, websocket):
        print("[音效姬] 开始接收消息喵...")
        while True:
            try:
                recvBuf = await websocket.recv()
                resp = proto.Proto()
                resp.unpack(recvBuf)
                # Process the response and handle audio playback
                if resp.ver == 0 and resp.body:
                    try:
                        message = resp.body.decode('utf-8')
                        if len(message) > 100:
                            data = json.loads(message)
                            cmd = data.get('cmd')
                            
                            if cmd == "LIVE_OPEN_PLATFORM_LIKE" or cmd == "OPEN_LIVEROOM_LIKE": #点赞
                                data_set = data.get("data")
                                like_count = int(data_set.get("like_count"))
                                user_id = data_set.get("uname", str(time.time()))  # Use timestamp as fallback if no uid
                                # Get probability setting for like sounds
                                like_probability = self.config.get('probabilitySettings', {}).get('likeSound', 1.0)
                                # Create a separate task for this user's likes
                                async def play_like_sounds(count):
                                    if not self.config.get('multiLikeEnabled', True):
                                        count = 1  # Only play once if multiLike is disabled
                                    elif count > 5:
                                        count = 5  # Cap at 5 sounds
                                    for _ in range(count):
                                        if random.random() < like_probability:
                                            self.sound_manager.play_audio('like')
                                            await asyncio.sleep(1.2)  # Shorter delay for better overlap
                                # Schedule the task without waiting
                                asyncio.create_task(play_like_sounds(like_count))
                                print(f"[音效姬] 收到来自用户 {user_id} 的点赞喵~！")
                                print(f"[音效姬] 收到指令: {cmd} 喵~！")
                                print(f"[音效姬] 点赞触发概率: {like_probability} 喵~！")
                            elif cmd == "LIVE_OPEN_PLATFORM_SEND_GIFT": #发送礼物
                                gift_data = data.get("data")
                                price = int(gift_data.get("price"))
                                if price <= 1000:
                                    self.sound_manager.play_audio("gift1")
                                elif price <= 10000:
                                    self.sound_manager.play_audio("gift2")
                                else:
                                    self.sound_manager.play_audio("gift3")
                                print(f"[音效姬] 收到礼物指令: {cmd}, 价值 {price} 喵~！")
                            elif cmd == "LIVE_OPEN_PLATFORM_DM": #发送弹幕
                                # Get probability setting for message sounds
                                message_probability = self.config.get('probabilitySettings', {}).get('messageSound', 1.0)
                                if random.random() < message_probability:
                                    self.sound_manager.play_audio("message")
                                print(f"[音效姬] 收到指令: {cmd} 喵~！")
                                print(f"[音效姬] 弹幕触发概率: {message_probability}喵~！")
                            elif cmd == "OPEN_LIVEROOM_SUPER_CHAT": #醒目留言
                                self.sound_manager.play_audio("superChat")
                                print(f"[音效姬] 收到醒目留言喵~！")
                            elif cmd == "OPEN_LIVEROOM_GUARD": #开通大航海
                                self.sound_manager.play_audio("guard")
                                print(f"[音效姬] 收到舰长开通喵~！")
                            elif cmd == "OPEN_LIVEROOM_LIVE_ROOM_ENTER": #进入
                                data_set = data.get("data")
                                user_id = data_set.get("uname", str(time.time()))  # Use timestamp as fallback if no uid
                                self.sound_manager.play_audio("enter")
                                print(f"[音效姬] {user_id}进入直播间喵~！")
                            elif cmd == "OPEN_LIVEROOM_INTERACT_WORD": #关注
                                data_obj = data.get("data", {})
                                msg_type = data_obj.get("msg_type", 0)
                                if msg_type == 2:  # Follow event
                                    self.sound_manager.play_audio("follow")
                                    data_set = data.get("data")
                                    user_id = data_set.get("uname", str(time.time()))  # Use timestamp as fallback if no 
                                    print(f"[音效姬] 新增关注: {user_id} 喵~！")
                    except Exception as e:
                        print(f"[音效姬] 处理消息时发生错误: {e}")
            except Exception as e:
                print(f"[音效姬] 接收消息时发生错误: {e}")
                await asyncio.sleep(1)  # Add delay before retry

    # 建立连接
    async def connect(self):
        addr, authBody = self.getWebsocketInfo()
        websocket = await websockets.connect(addr)
        # 鉴权
        await self.auth(websocket, authBody)
        return websocket

    def __enter__(self):
        print("[音效姬] 启动喵~！")

    def __exit__(self, type, value, trace):
        # 关闭应用
        postUrl = "%s/v2/app/end" % self.host
        params = '{"game_id":"%s","app_id":%d}' % (self.gameId, self.appId)
        headerMap = self.sign(params)
        r = requests.post(url=postUrl, headers=headerMap,
                          data=params, verify=False)
        print("[音效姬] 应用关闭成功")


if __name__ == '__main__':
    config = load_config()
    idCode = config['idCode']
    if not idCode:
        print("[音效姬] 错误: 未配置idCode。请先在PeiZhiWenJian.exe的网页界面中设置 TnT")
        time.sleep(5)
        
    try:
        cli = BiliClient(
            idCode=idCode,  # Read from config
            appId=1740051020209,  # 应用id
            key="UIITOOvJBq2L3qSe0RPULFSt",  # access_key
            secret="ucBpEQejW1bd5n9PpcuZ9FFHIoIrjq",  # access_key_secret
            host="https://live-open.biliapi.com") # 开放平台 (线上环境)
        with cli:
            cli.run()
    except KeyboardInterrupt:
        print("[音效姬] 收到键盘中断信号，正在退出...")
    except Exception as e:
        print(f"[音效姬] 错误: {e}")
        
