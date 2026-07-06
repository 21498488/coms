from serial.tools import list_ports

HUB_PORT_1 =   "USB VID:PID=0403:6001 SER=B001OB7X"
HUB_PORT_2 =   "USB VID:PID=0403:6001 SER=B001OB7U"
HUB_PORT_3 =   "USB VID:PID=0403:6001 SER=B001OB81"
HUB_PORT_4 =   "USB VID:PID=0403:6001 SER=B001OB7Y"
HUB_PORT_5 =   "USB VID:PID=0403:6001 SER=B001OB82"
HUB_PORT_6 =   "USB VID:PID=0403:6001 SER=B001OB85"
HUB_PORT_7 =   "USB VID:PID=0403:6001 SER=B001OB86"
HUB_PORT_8 =   "USB VID:PID=0403:6001 SER=B001OB7T"

def port_by_hwid(hardwareId):
    ports = list_ports.comports()
    for port in ports:
        if hardwareId in port.hwid:
            return port.device
    return "<Unresolvable HWID " + hardwareId + ">"

def get_all_ports():
    ports = list_ports.comports()
    portnames = []
    for port in ports:
        portnames.append(port.device)
    # Shorter names first e.g. so that COM2 is before COM11
    portnames.sort(key=lambda s: (len(s), s))
    return portnames

def print_port_info():
    ports = list_ports.comports()
    for port in ports:
        print(port.device, "\t", port.description, "\tHWID:", port.hwid)
