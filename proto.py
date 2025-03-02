import struct

class Proto:
    def __init__(self):
        # Protocol related attributes
        self.packetLen = 0
        self.headerLen = 16
        self.ver = 0
        self.op = 0
        self.seq = 0
        self.body = ''
        self.maxBody = 2048
    
    def pack(self):
        """Pack data into a binary format"""
        self.packetLen = len(self.body) + self.headerLen
        return struct.pack(
            '>ihhii', 
            self.packetLen,
            self.headerLen,
            self.ver,
            self.op,
            self.seq
        ) + self.body.encode()
    
    def unpack(self, buf):
        """Unpack binary data into object attributes"""
        if len(buf) < self.headerLen:
            print("Insufficient header length")
            return
            
        try:
            self.packetLen = struct.unpack('>i', buf[0:4])[0]
            self.headerLen = struct.unpack('>h', buf[4:6])[0]
            self.ver = struct.unpack('>h', buf[6:8])[0]
            self.op = struct.unpack('>i', buf[8:12])[0]
            self.seq = struct.unpack('>i', buf[12:16])[0]
            
            if not self._validate_packet(buf):
                return
                
            self.body = buf[16:self.packetLen]
            #if len(self.body) > 0 and self.ver == 0:
                #print("====> callback:", self.body.decode('utf-8'))
        except struct.error as e:
            print(f"Error unpacking data: {e}")
    
    def _validate_packet(self, buf):
        """Validate packet data"""
        if self.packetLen < 0 or self.packetLen > self.maxBody:
            print(f"Invalid packet length: {self.packetLen}")
            return False
            
        if self.headerLen != 16:  # Fixed header length
            print("Invalid header length")
            return False
            
        if len(buf) < self.packetLen:
            print("Incomplete packet data")
            return False
            
        return True
