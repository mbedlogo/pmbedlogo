
import serial
from serial.tools import list_ports

eSector = 0x0e
e = 0xe000
g = 0x2007c000

class mbedLogo():

    def __init__(self, port='/dev/ttyACM0', baudrate=9600, timeout=0.2):
        mbed_port = self.list_mbed()
        self.mbed = serial.Serial(mbed_port, baudrate, timeout=timeout)

    def list_mbed(self):
        return [port[0] for port in list_ports.grep('ttyACM')][0]

    def __exit__(self):
        self.mbed.close()

    def bytes_available(self):
        return self.mbed.inWaiting()

    def read(self):
        """Reads response from the mbed"""
        response = []
        while True:
            data = self.mbed.read()
            if data != '':
                response.append(ord(data))
            else:
                break
        return response

    def read_ascii(self):
        """Reads response from the mbed in ASCII"""
        response = self.read()
        if len(response) != 0:
            response_str = ''
            for i in response:
                if i != 255 and i != '\n':
                    response_str = response_str + chr(i)
            return '  %s\r' %response_str
        else:
            return '\r'

    def write(self, data):
        """Writes one byte to the mbed

        Args:
            mbed: mbed serial device
            data: byte to be sent

        """
        self.mbed.write(chr(data & 0xff))

    def write16(self, data):
        """Writes two bytes to the mbed

        Args:
            mbed: mbed serial device
            data: bytes to be sent

        """
        for i in range(2):
            self.mbed.write(chr(data & 0xff))
            data = data / 256

    def write32(self, data):
        """Writes three bytes to the mbed

        Args:
            mbed: mbed serial device
            data: bytes to be sent

        """
        for i in range(4):
            self.mbed.write(chr(data & 0xff))
            data = data / 256

    def test_communication(self):
        """Tests the communication with the mbed

        Args:
            mbed: mbed serial device
        Returns:
            interger number 23

        """
        self.write(0xff)
        return self.read()

    def read_memory(self, address, count):
        """Reads count bytes from memory starting at address

        Args:
            mbed:     mbed serial device
            address:  start address to read
            count:    number of bytes
        Returns:
            a list with the readings

        """
        self.write(0xfe)        # Send the read memory opcode
        self.write32(address)    # Send the 32 bits start address (4 bytes)
        self.write16(count)    # Send how many bytes we want to read (2 bytes)
        return self.read()    # Read the number of bytes from the device

    def write_memory(self, address, data):
        """Writes bytes to the RAM memory starting at address

        Args:
            mbed:     mbed serial device
            address:  start address to write
            data:     list of bytes
        Returns:
            a number 0

        """
        self.write(0xfd)        # Send the write memory opcode
        self.write32(address)    # Send the 32 bits destination address (4 bytes)
        self.write16(len(data))    # Send how many bytes we want to write (2 bytes)
        for i in range(len(data)):    # Write data
            self.write(data[i])
        return self.read()

    def write_flash(self, sector, address, data):
        """Writes bytes to the FLASH memory starting at address in sector

        Args:
            mbed:     mbed serial device
            sector:   sector of the FLASH memory
            address:  start address to write
            data:     list of bytes
        Returns:
            zero if the write was sucesfull

        """
        response = -1
        while len(data) != 0:
            count = min(256, len(data))
            self.write(0xfb)        # Send the write flash opcode
            self.write(sector)      # Send the sector to write
            self.write32(address)   # Send the 32 bits destination address (4 bytes)
            self.write(count)       # Send how many bytes we want to write (1 byte)
            for i in range(count):      # Write data
                self.write(data[i])
            address = address + count
            data = data[count:]
            response = self.read()
        return response

    def erase_flash(self, sector):
        """Erases flash address at sector

        Args:
            mbed:     mbed serial device
            sector:   sector of the FLASH memory
        Returns:
            zero if the erase was sucesfull

        """
        self.write(0xfa)        # Send the erase flash opcode
        self.write(sector)        # Send the sector to write
        return self.read()

    def run_command(self, command):
        """Writes compiled Logo command to the FLASH memory and runs it

        Args:
            mbed:     mbed serial device
            command:  list with compiled Logo command 

        """
        self.erase_flash(eSector)    # Erase flash sector
        self.write_flash(eSector, e, command)    # Write command to flash
        self.write(0xfc)        # Send the run opcode
