# Copyright (C) 2022, ServiceA3
# Copyright (C) 2018, Andrea Tuccia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import asyncio
from collections import OrderedDict as OD
import random
import re
import socket
import threading
import time
import uuid

from lxml import etree
import xmltodict


class ConnectionError(Exception):
    pass


class PushClientError(Exception):
    pass


class ClientError(Exception):
    pass


class LoginError(Exception):
    pass


class ResponseError(Exception):
    pass


class iAlarmMkClient:

    seq = 0
    timeout = 10

    def __init__(self, host, port, uid, pwd, logger):
        self.sock = None

        self.host = host
        self.port = port
        self.uid = uid
        self.pwd = pwd
        self.token = None
        self.logger = logger

    def __del__(self):
        self.logout()

    def is_socket_connected(self):
        '''Controlla se il socket è già connesso. Se non è connesso inizializza un nuovo socket.'''
        self._print(f"Socket file descriptor:{self.sock.fileno()}.")
        try:
            # Se il socket è connesso, restituisce l'indirizzo del peer
            self.sock.getpeername()
            self._print("Socket already connected.")
        except OSError as e:
            # Il socket non è connesso e lo reinizializza, cattura l'errore e restituisce False
            self._print(f"Socket is not connected, error messagge: {e}. Proceding to close old socket.")
            self.close_socket()
            self._print("Re-initialized new socket, creating a new socket.")
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            return False
        return True

    def login(self):
        self._print("Login method called.")
        '''Controlla se il socket è inizializzato e valido.'''
        if self.sock is None or self.sock.fileno() == -1:
            self._print("Invalid or uninitialized socket, creating a new socket.")
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Controllo se il socket è già connesso
        self._print("Checking if the socket is already connected.")
        if not self.is_socket_connected():
            self._print("Socket not connected, setting timeout and attempting to connect.")
            self.sock.settimeout(self.timeout)
            try:
                self._print("Attempting to connect to the server.")
                self.sock.connect((self.host, self.port))
                self._print("Connection successful, proceeding with login to server.")

                # Preparazione dei dati di login
                cmd = OD()
                cmd["Id"] = STR(self.uid)
                cmd["Pwd"] = PWD(self.pwd)
                cmd["Type"] = "TYP,ANDROID|0"
                self.token = uuid.uuid4()
                cmd["Token"] = STR(str(self.token))
                cmd["Action"] = "TYP,IN|0"
                cmd["PemNum"] = "STR,5|26"
                cmd["DevVersion"] = None
                cmd["DevType"] = None
                cmd["Err"] = None
                xpath = "/Root/Pair/Client"

                # Invio dei dati al server
                self.client = self._(xpath, cmd)

                # Controllo degli errori nella risposta del server
                if self.client["Err"]:
                    self._print(f"Error during login to the server: {self.client['Err']}, token used is {self.token}")
                    self.close_socket()
                    raise ClientError("Login error")
                self._print(f"Login ok, token used is {self.token}")

            except TimeoutError as e:
                self._print(f"Connection timeout: {e}")
                self.close_socket()
                raise ConnectionError("Connection error: timeout") from e

            except ConnectionRefusedError as e:
                self._print(f"Connection refused by the server: {e}")
                self.close_socket()
                raise ConnectionError("Connection error: connection refused") from e

            except OSError as e:
                self._print(f"Network error: {e}")
                self.close_socket()
                raise ConnectionError("Connection error: network error") from e

            except Exception as e:
                self._print(f"Unexpected error during login: {e}")
                self.close_socket()
                raise ClientError("Unexpected error during login") from e

    def close_socket(self):
        """Funzione ausiliaria per chiudere il socket in modo sicuro."""
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except Exception as e:
                self._print(f"Error closing socket: {e}")
            finally:
                self.sock = None
                self._print(f"Closed socket with token: {self.token}")
                self.token = None

    def logout(self):
        self._print("Logout method called.")
        if self.sock is None:
            return
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        self.sock = None
        self._print(f"Logout socket with token: {self.token}")
        self.token = None

    def GetAlarmStatus(self):
        cmd = OD()
        cmd["DevStatus"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetAlarmStatus"
        return self._(xpath, cmd)

    def GetByWay(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetByWay"
        return self._(xpath, cmd, True)

    def GetDefense(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetDefense"
        return self._(xpath, cmd, True)

    def GetEmail(self):
        cmd = OD()
        cmd["Ip"] = None
        cmd["Port"] = None
        cmd["User"] = None
        cmd["Pwd"] = None
        cmd["EmailSend"] = None
        cmd["EmailRecv"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetEmail"
        return self._(xpath, cmd)

    def GetEvents(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetEvents"
        return self._(xpath, cmd, True)

    def GetGprs(self):
        cmd = OD()
        cmd["Apn"] = None
        cmd["User"] = None
        cmd["Pwd"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetGprs"
        return self._(xpath, cmd)

    def GetLog(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetLog"
        return self._(xpath, cmd, True)

    def GetNet(self):
        cmd = OD()
        cmd["Mac"] = None
        cmd["Name"] = None
        cmd["Ip"] = None
        cmd["Gate"] = None
        cmd["Subnet"] = None
        cmd["Dns1"] = None
        cmd["Dns2"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetNet"
        return self._(xpath, cmd)

    def GetOverlapZone(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetOverlapZone"
        return self._(xpath, cmd, True)

    def GetPairServ(self):
        cmd = OD()
        cmd["Ip"] = None
        cmd["Port"] = None
        cmd["Id"] = None
        cmd["Pwd"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetPairServ"
        return self._(xpath, cmd)

    def GetPhone(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["RepeatCnt"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetPhone"
        return self._(xpath, cmd, True)

    def GetRemote(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetRemote"
        return self._(xpath, cmd, True)

    def GetRfid(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetRfid"
        return self._(xpath, cmd, True)

    def GetRfidType(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetRfidType"
        return self._(xpath, cmd, True)

    def GetSendby(self, cid):
        cmd = OD()
        cmd["Cid"] = STR(cid)
        cmd["Tel"] = None
        cmd["Voice"] = None
        cmd["Sms"] = None
        cmd["Email"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetSendby"
        return self._(xpath, cmd)

    def GetSensor(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetSensor"
        return self._(xpath, cmd, True)

    def GetServ(self):
        cmd = OD()
        cmd["En"] = None
        cmd["Ip"] = None
        cmd["Port"] = None
        cmd["Name"] = None
        cmd["Pwd"] = None
        cmd["Cnt"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetServ"
        return self._(xpath, cmd)

    def GetSwitch(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetSwitch"
        return self._(xpath, cmd, True)

    def GetSwitchInfo(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetSwitchInfo"
        return self._(xpath, cmd, True)

    def GetSys(self):
        cmd = OD()
        cmd["InDelay"] = None
        cmd["OutDelay"] = None
        cmd["AlarmTime"] = None
        cmd["WlLoss"] = None
        cmd["AcLoss"] = None
        cmd["ComLoss"] = None
        cmd["ArmVoice"] = None
        cmd["ArmReport"] = None
        cmd["ForceArm"] = None
        cmd["DoorCheck"] = None
        cmd["BreakCheck"] = None
        cmd["AlarmLimit"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetSys"
        return self._(xpath, cmd)

    def GetTel(self):
        cmd = OD()
        cmd["En"] = None
        cmd["Code"] = None
        cmd["Cnt"] = None
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetTel"
        return self._(xpath, cmd, True)

    def GetTime(self):
        cmd = OD()
        cmd["En"] = None
        cmd["Name"] = None
        cmd["Type"] = None
        cmd["Time"] = None
        cmd["Dst"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetTime"
        return self._(xpath, cmd)

    def GetVoiceType(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetVoiceType"
        return self._(xpath, cmd, True)

    def GetZone(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetZone"
        return self._(xpath, cmd, True)

    def GetZoneType(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetZoneType"
        return self._(xpath, cmd, True)

    def WlsStudy(self):
        cmd = OD()
        cmd["Err"] = None
        xpath = "/Root/Host/WlsStudy"
        return self._(xpath, cmd)

    def ConfigWlWaring(self):
        cmd = OD()
        cmd["Err"] = None
        xpath = "/Root/Host/ConfigWlWaring"
        return self._(xpath, cmd)

    def FskStudy(self, en):
        cmd = OD()
        cmd["Study"] = BOL(en)
        cmd["Err"] = None
        xpath = "/Root/Host/FskStudy"
        return self._(xpath, cmd)

    def GetWlsStatus(self, num):
        cmd = OD()
        cmd["Num"] = S32(num)
        cmd["Bat"] = None
        cmd["Tamp"] = None
        cmd["Status"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetWlsStatus"
        return self._(xpath, cmd)

    def DelWlsDev(self, num):
        cmd = OD()
        cmd["Num"] = S32(num)
        cmd["Err"] = None
        xpath = "/Root/Host/DelWlsDev"
        return self._(xpath, cmd)

    def WlsSave(self, typ, num, code):
        cmd = OD()
        cmd["Type"] = "TYP,NO|%d" % typ
        cmd["Num"] = S32(num, 1)
        cmd["Code"] = STR(code)
        cmd["Err"] = None
        xpath = "/Root/Host/WlsSave"
        return self._(xpath, cmd)

    def GetWlsList(self):
        cmd = OD()
        cmd["Total"] = None
        cmd["Offset"] = S32(0)
        cmd["Ln"] = None
        cmd["Err"] = None
        xpath = "/Root/Host/GetWlsList"
        return self._(xpath, cmd)

    def SwScan(self):
        cmd = OD()
        cmd["Err"] = None
        xpath = "/Root/Host/SwScan"
        return self._(xpath, cmd)

    def Reset(self, ret):
        cmd = OD()
        cmd["Ret"] = BOL(ret)
        cmd["Err"] = None
        xpath = "/Root/Host/Reset"
        return self._(xpath, cmd)

    def OpSwitch(self, pos, en):
        cmd = OD()
        cmd["Pos"] = S32(pos, 1)
        cmd["En"] = BOL(en)
        cmd["Err"] = None
        xpath = "/Root/Host/OpSwitch"
        return self._(xpath, cmd)

    def SetAlarmStatus(self, status):
        cmd = OD()
        cmd["DevStatus"] = TYP(status, ["ARM", "DISARM", "STAY", "CLEAR","","","","","PARTIAL"])
        cmd["Err"] = None
        xpath = "/Root/Host/SetAlarmStatus"
        return self._(xpath, cmd)

    def SetByWay(self, pos, en):
        cmd = OD()
        cmd["Pos"] = S32(pos, 1)
        cmd["En"] = BOL(en)
        cmd["Err"] = None
        xpath = "/Root/Host/SetByWay"
        return self._(xpath, cmd)

    def SetDefense(self, pos, hmdef="00:00", hmundef="00:00"):
        cmd = OD()
        cmd["Pos"] = S32(pos, 1)
        cmd["Def"] = STR(hmdef)
        cmd["Undef"] = STR(hmundef)
        cmd["Err"] = None
        xpath = "/Root/Host/SetDefense"
        return self._(xpath, cmd)

    def SetEmail(self, ip, port, user, pwd, emailsend, emailrecv):
        cmd = OD()
        cmd["Ip"] = STR(ip)
        cmd["Port"] = S32(port)
        cmd["User"] = STR(user)
        cmd["Pwd"] = PWD(pwd)
        cmd["EmailSend"] = STR(emailsend)
        cmd["EmailRecv"] = STR(emailrecv)
        cmd["Err"] = None
        xpath = "/Root/Host/SetEmail"
        return self._(xpath, cmd)

    def SetGprs(self, apn, user, pwd):
        cmd = OD()
        cmd["Apn"] = STR(apn)
        cmd["User"] = STR(user)
        cmd["Pwd"] = PWD(pwd)
        cmd["Err"] = None
        xpath = "/Root/Host/SetGprs"
        return self._(xpath, cmd)

    def SetNet(self, mac, name, ip, gate, subnet, dns1, dns2):
        cmd = OD()
        cmd["Mac"] = MAC(mac)
        cmd["Name"] = STR(name)
        cmd["Ip"] = IPA(ip)
        cmd["Gate"] = IPA(gate)
        cmd["Subnet"] = IPA(subnet)
        cmd["Dns1"] = IPA(dns1)
        cmd["Dns2"] = IPA(dns2)
        cmd["Err"] = None
        xpath = "/Root/Host/SetNet"
        return self._(xpath, cmd)

    def SetOverlapZone(self, pos, zone1, zone2, time):
        cmd = OD()
        cmd["Pos"] = S32(pos, 1)
        cmd["Zone1"] = S32(pos, 1)
        cmd["Zone1"] = S32(pos, 1)
        cmd["Time"] = S32(pos, 1)
        cmd["Err"] = None
        xpath = "/Root/Host/SetOverlapZone"
        return self._(xpath, cmd)

    def SetPairServ(self, ip, port, uid, pwd):
        cmd = OD()
        cmd["Ip"] = IPA(ip)
        cmd["Port"] = S32(port, 1)
        cmd["Id"] = STR(uid)
        cmd["Pwd"] = PWD(pwd)
        cmd["Err"] = None
        xpath = "/Root/Host/SetPairServ"
        return self._(xpath, cmd)

    def SetPhone(self, pos, num):
        cmd = OD()
        cmd["Type"] = TYP(1, ["F", "L"])
        cmd["Pos"] = S32(pos, 1)
        cmd["Num"] = STR(num)
        cmd["Err"] = None
        xpath = "/Root/Host/SetPhone"
        return self._(xpath, cmd)

    def SetRfid(self, pos, code, typ, msg):
        cmd = OD()
        cmd["Pos"] = S32(pos, 1)
        cmd["Type"] = S32(typ, ["NO", "DS", "HS", "DM", "HM", "DC"])
        cmd["Code"] = STR(code)
        cmd["Msg"] = STR(msg)
        cmd["Err"] = None
        xpath = "/Root/Host/SetRfid"
        return self._(xpath, cmd)

    def SetRemote(self, pos, code):
        cmd = OD()
        cmd["Pos"] = S32(pos, 1)
        cmd["Code"] = STR(code)
        cmd["Err"] = None
        xpath = "/Root/Host/SetRemote"
        return self._(xpath, cmd)

    def SetSendby(self, cid, tel, voice, sms, email):
        cmd = OD()
        cmd["Cid"] = STR(cid)
        cmd["Tel"] = BOL(tel)
        cmd["Voice"] = BOL(voice)
        cmd["Sms"] = BOL(sms)
        cmd["Email"] = BOL(email)
        cmd["Err"] = None
        xpath = "/Root/Host/SetSendby"
        return self._(xpath, cmd)

    def SetSensor(self, pos, code):
        cmd = OD()
        cmd["Pos"] = S32(pos, 1)
        cmd["Code"] = STR(code)
        cmd["Err"] = None
        xpath = "/Root/Host/SetSensor"
        return self._(xpath, cmd)

    def SetServ(self, en, ip, port, name, pwd, cnt):
        cmd = OD()
        cmd["En"] = BOL(en)
        cmd["Ip"] = STR(ip)
        cmd["Port"] = S32(port, 1)
        cmd["Name"] = STR(name)
        cmd["Pwd"] = PWD(pwd)
        cmd["Cnt"] = S32(cnt, 1)
        cmd["Err"] = None
        xpath = "/Root/Host/SetServ"
        return self._(xpath, cmd)

    def SetSwitch(self, pos, code):
        cmd = OD()
        cmd["Pos"] = S32(pos, 1)
        cmd["Code"] = STR(code)
        cmd["Err"] = None
        xpath = "/Root/Host/SetSwitch"
        return self._(xpath, cmd)

    def SetSwitchInfo(self, pos, name, hmopen="00:00", hmclose="00:00"):
        cmd = OD()
        cmd["Pos"] = S32(pos, 1)
        cmd["Name"] = STR(name[:7].encode("hex"))
        cmd["Open"] = STR(hmopen)
        cmd["Close"] = STR(hmclose)
        cmd["Err"] = None
        xpath = "/Root/Host/SetSwitchInfo"
        return self._(xpath, cmd)

    def SetSys(
        self,
        indelay,
        outdelay,
        alarmtime,
        wlloss,
        acloss,
        comloss,
        armvoice,
        armreport,
        forcearm,
        doorcheck,
        breakcheck,
        alarmlimit,
    ):
        cmd = OD()
        cmd["InDelay"] = S32(indelay, 1)
        cmd["OutDelay"] = S32(outdelay, 1)
        cmd["AlarmTime"] = S32(alarmtime, 1)
        cmd["WlLoss"] = S32(wlloss, 1)
        cmd["AcLoss"] = S32(acloss, 1)
        cmd["ComLoss"] = S32(comloss, 1)
        cmd["ArmVoice"] = BOL(armvoice)
        cmd["ArmReport"] = BOL(armreport)
        cmd["ForceArm"] = BOL(forcearm)
        cmd["DoorCheck"] = BOL(doorcheck)
        cmd["BreakCheck"] = BOL(breakcheck)
        cmd["AlarmLimit"] = BOL(alarmlimit)
        cmd["Err"] = None
        xpath = "/Root/Host/SetSys"
        return self._(xpath, cmd)

    def SetTel(self, en, code, cnt):
        cmd = OD()
        cmd["Typ"] = TYP(0, ["F", "L"])
        cmd["En"] = BOL(en)
        cmd["Code"] = int(code)
        cmd["Cnt"] = S32(cnt, 1)
        cmd["Err"] = None
        xpath = "/Root/Host/SetTel"
        return self._(xpath, cmd)

    def SetTime(self, en, name, typ, time, dst):
        cmd = OD()
        cmd["En"] = BOL(en)
        cmd["Name"] = STR(name)
        cmd["Type"] = "TYP,0|%d" % typ
        cmd["Time"] = DTA(time)
        cmd["Dst"] = BOL(dst)
        cmd["Err"] = None
        xpath = "/Root/Host/SetTime"
        return self._(xpath, cmd)

    def SetZone(self, pos, typ, voice, name, bell):
        cmd = OD()
        cmd["Pos"] = S32(pos, 1)
        cmd["Type"] = TYP(
            typ, ["NO", "DE", "SI", "IN", "FO", "HO24", "FI", "KE", "GAS", "WT"]
        )
        cmd["Voice"] = TYP(voice, ["CX", "MC", "NO"])
        cmd["Name"] = STR(name)
        cmd["Bell"] = BOL(bell)
        cmd["Err"] = None
        xpath = "/Root/Host/SetZone"
        return self._(xpath, cmd)

    def _print(self, data):
        if self.logger is not None:
            self.logger.debug(str(data))
        else:
            print(str(data))

    def _(self, xpath, cmd, is_list=False, offset=0, l=None):
        if offset > 0:
            cmd["Offset"] = S32(offset)
        root = self._create(xpath, cmd)
        self._send(root)
        resp = self._receive()
        #self._print(f"*** response: \n{resp}\n**********")
        if is_list == False:
            return self._select(resp, xpath)
        if l is None:
            l = []
        total = self._select(resp, "%s/Total" % xpath)
        ln = self._select(resp, "%s/Ln" % xpath)
        for i in list(range(ln)):
            event = self._select(resp, "%s/L%d" % (xpath, i))
            l.append(self._select(resp, "%s/L%d" % (xpath, i)))
        offset += ln
        if total > offset:
            self._(xpath, cmd, is_list, offset, l)
        return l

    def _send(self, root):
        try:
            xml: str = etree.tostring(self._convert_dict_to_xml(root), pretty_print=False)
            self.seq += 1
            mesg = b"@ieM%04d%04d0000%s%04d" % (
                len(xml),
                self.seq,
                self._xor(xml),
                self.seq,
            )
            self.sock.sendall(mesg)
        except OSError as e:
            self.logger.error("Error during sending message: %s", e)
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
            raise


    def _receive(self):
        try:
            data = self.sock.recv(1024)
            if not data:
                self._print("Connection close from server (recv == b'')")
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
                raise ConnectionError("Connection close from server")

            self._print(f"Data received, length: {len(data)}")

            # Parsiamo solo se data è valido
            payload = self._xor(data[16:-4]).decode()
            return xmltodict.parse(
                payload,
                xml_attribs=False,
                dict_constructor=dict,
                postprocessor=self._xmlread,
            )

        except TimeoutError as e:
            raise ConnectionError("Timeout during receive from server") from e

        except OSError as e:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
            raise ConnectionError(f"Connection error: {e}") from e


    def _xor(self, input):
        sz = bytearray.fromhex(
            "0c384e4e62382d620e384e4e44382d300f382b382b0c5a6234384e304e4c372b10535a0c20432d171142444e58422c421157322a204036172056446262382b5f0c384e4e62382d620e385858082e232c0f382b382b0c5a62343830304e2e362b10545a0c3e432e1711384e625824371c1157324220402c17204c444e624c2e12"
        )
        buf = bytearray(input)
        for i in range(len(input)):
            ki = i & 0x7F
            buf[i] = buf[i] ^ sz[ki]
        return buf

    def _create(self, path, mydict={}):
        root = {}
        elem = root
        try:
            plist = path.strip("/").split("/")
            k = len(plist) - 1
            for i, j in enumerate(plist):
                elem[j] = {}
                if i == k:
                    elem[j] = mydict
                elem = elem.get(j)
        except:
            pass
        return root

    def _select(self, mydict, path):
        elem = mydict
        try:
            for i in path.strip("/").split("/"):
                try:
                    i = int(i)
                    elem = elem[i]
                except ValueError:
                    elem = elem.get(i)
        except:
            pass
        return elem

    def _xmlread(self, path, key, value):
        try:
            input = value
            BOL = re.compile(r"BOL\|([FT])")
            DTA = re.compile(r"DTA(,\d+)*\|(\d{4}\.\d{2}.\d{2}.\d{2}.\d{2}.\d{2})")
            ERR = re.compile(r"ERR\|(\d{2})")
            GBA = re.compile(r"GBA,(\d+)\|([0-9A-F]*)")
            HMA = re.compile(r"HMA,(\d+)\|(\d{2}:\d{2})")
            IPA = re.compile(r"IPA,(\d+)\|(([0-2]?\d{0,2}\.){3}([0-2]?\d{0,2}))")
            MAC = re.compile(r"MAC,(\d+)\|(([0-9A-F]{2}[:-]){5}([0-9A-F]{2}))")
            NEA = re.compile(r"NEA,(\d+)\|([0-9A-F]+)")
            NUM = re.compile(r"NUM,(\d+),(\d+)\|(\d*)")
            PWD = re.compile(r"PWD,(\d+)\|(.*)")
            S32 = re.compile(r"S32,(\d+),(\d+)\|(\d*)")
            STR = re.compile(r"STR,(\d+)\|(.*)")
            TYP = re.compile(r"TYP,(\w+)\|(\d+)")
            if BOL.match(input):
                bol = BOL.search(input).groups()[0]
                if bol == "T":
                    value = True
                if bol == "F":
                    value = False
            elif DTA.match(input):
                dta = DTA.search(input).groups()[1]
                value = time.strptime(dta, "%Y.%m.%d.%H.%M.%S")
            elif ERR.match(input):
                value = int(ERR.search(input).groups()[0])
            elif GBA.match(input):
                value = bytearray.fromhex(GBA.search(input).groups()[1]).decode()
            elif HMA.match(input):
                hma = HMA.search(input).groups()[1]
                value = time.strptime(hma, "%H:%M")
            elif IPA.match(input):
                value = str(IPA.search(input).groups()[1])
            elif MAC.match(input):
                value = str(MAC.search(input).groups()[1])
            elif NEA.match(input):
                value = str(NEA.search(input).groups()[1])
            elif NUM.match(input):
                value = str(NUM.search(input).groups()[2])
            elif PWD.match(input):
                value = str(PWD.search(input).groups()[1])
            elif S32.match(input):
                value = int(S32.search(input).groups()[2])
            elif STR.match(input):
                value = str(STR.search(input).groups()[1])
            elif TYP.match(input):
                value = int(TYP.search(input).groups()[1])
            else:
                raise ResponseError(f"Unknown data type {format(input)}")
            return key, value
        except (ValueError, TypeError):
            return key, value

    @staticmethod
    def _convert_dict_to_xml_recurse(parent: etree.Element, dictitem: dict) -> None:
        assert not isinstance(dictitem, type([]))

        if isinstance(dictitem, dict):
            for (tag, child) in dictitem.items():
                if isinstance(child, type([])):
                    # iterate through the array and convert
                    for list_child in child:
                        elem: etree.Element = etree.Element(tag)
                        parent.append(elem)
                        iAlarmMkClient._convert_dict_to_xml_recurse(elem, list_child)
                else:
                    elem = etree.Element(tag)
                    parent.append(elem)
                    iAlarmMkClient._convert_dict_to_xml_recurse(elem, child)
        elif dictitem is not None:
            # None Element should be written without "None" value
            parent.text = str(dictitem)

    @staticmethod
    def _convert_dict_to_xml(xmldict: dict):
        # Converts a dictionary to an XML ElementTree Element
        root_tag = list(xmldict.keys())[0]
        root: etree.Element = etree.Element(root_tag)
        iAlarmMkClient._convert_dict_to_xml_recurse(root, xmldict[root_tag])
        return root


class iAlarmMkPushClient(asyncio.Protocol, iAlarmMkClient):

    daemon = True
    keepalive = 60
    timeout = 10

    def __init__(self, host, port, uid, handler, loop, on_con_lost, threadID, logger=None):
        if not callable(handler):
            raise AttributeError("handler is not a function")
        self.host = host
        self.port = port
        self.handler = handler
        cmd = OD()
        cmd["Id"] = STR(uid)
        cmd["Err"] = None
        xpath = "/Root/Pair/Push"
        self.mesg = self._create(xpath, cmd)
        #self._thread_sockets = dict()
        self.loop = loop
        self.on_con_lost = on_con_lost
        self.transport = None
        self.threadID = threadID
        self.logger = logger

        # asyncore.dispatcher.__init__(self, map=self._thread_sockets)

    def connection_made(self, transport: asyncio.transports.Transport) -> None:
        self.transport = transport
        self.handle_write()
        self.handle_connect()

    def data_received(self, data: bytes) -> None:
        return self.handle_read(data)

    def connection_lost(self, exc):
        self._print("iAlarmMkPushClient - connection_lost exception: "+str(exc))
        self._close()

    def __del__(self):
        try:
            self._close()
        except AttributeError:
            pass
        else:
            self._close()

    def readable(self):
        return True

    def writable(self):
        if self.mesg is not None:
            return True
        return False

    def handle_connect(self):
        #threading.Timer(self.keepalive, self._keepalive).start()
        timer = threading.Timer(self.keepalive, self._keepalive)
        random_number = random.randint(100, 999)
        timer.name = f"{self.threadID}-{random_number}"
        timer.start()

    def handle_error(self):
        self._close()
        raise

    def handle_read(self, data):
        try:
            if type(data) == str:
                data = data.encode()
            head = data[0:4]

            # Logging dell'header e della lunghezza dei dati ricevuti
            self._print(f"iAlarmMkPushClient - handle_read - Header: {head}, Data Length: {len(data)}")

            resp = None

            if head == b"%maI":
                self._print("iAlarmMkPushClient - handle_read - Keepalive message received.")
                #threading.Timer(self.keepalive, self._keepalive).start()
                timer = threading.Timer(self.keepalive, self._keepalive)
                random_number = random.randint(100, 999)
                timer.name = f"{self.threadID}-{random_number}"
                timer.start()

            elif head == b"@ieM":
                self._print("iAlarmMkPushClient - handle_read - Pairing message received.")
                xpath = "/Root/Pair/Push"
                resp = xmltodict.parse(
                    self._xor(data[16:-4]).decode(),
                    xml_attribs=False,
                    dict_constructor=dict,
                    postprocessor=self._xmlread,
                )
                self.push = self._select(resp, xpath)
                if self.push:
                    err = self._select(resp, "%s/Err" % xpath)
                    if err:
                        self._print("iAlarmMkPushClient - handle_read - Pairing error detected, closing connection.")
                        self._close()
                        raise PushClientError("Push subscription error")
                    else:
                        self._print("iAlarmMkPushClient - handle_read - Device successfully paired.")
                else:
                    self._print("iAlarmMkPushClient - handle_read - No pairing information found.")
                    xpath = "/Root/Host/Alarm"
                    self._print(f"iAlarmMkPushClient - handle_read - Set handler - Processed Response: {resp}, xpath: {xpath}")
                    self.handler(self._select(resp, xpath))

            elif head == b"@alA":
                self._print("iAlarmMkPushClient - handle_read - Alarm message received.")
                xpath = "/Root/Host/Alarm"
                resp = xmltodict.parse(
                    self._xor(data[16:-4]).decode(),
                    xml_attribs=False,
                    dict_constructor=dict,
                    postprocessor=self._xmlread,
                )
                self._print(f"iAlarmMkPushClient - handle_read - Set handler - Processed Response: {resp}, xpath: {xpath}")
                self.handler(self._select(resp, xpath))

            elif head == b"!lmX":
                self._print("iAlarmMkPushClient - handle_read - Alternate alarm message received.")
                xpath = "/Root/Host/Alarm"
                resp = xmltodict.parse(
                    data[16:-4],
                    xml_attribs=False,
                    dict_constructor=dict,
                    postprocessor=self._xmlread,
                )
                self._print(f"iAlarmMkPushClient - handle_read - Set handler - Processed Response: {resp}, xpath: {xpath}")
                self.handler(self._select(resp, xpath))

            else:
                self._print(f"iAlarmMkPushClient - handle_read - Unrecognized header: {head}, closing connection.")
                self._close()
                raise ResponseError("Response error")

        except Exception as e:
            self._print(f"iAlarmMkPushClient - handle_read - Error: {str(e)}")
            raise

    def handle_write(self):
        if self.mesg is not None:
            xml: str = etree.tostring(
                self._convert_dict_to_xml(self.mesg), pretty_print=False
            )
            mesg = b"@ieM%04d%04d0000%s%04d" % (len(xml), 0, self._xor(xml), 0)
            self.transport.write(mesg)
            self.mesg = None

    def handle_close(self):
        self._close()

    def _close(self):
        self._print("Device connection close!")
        try:
            if self.transport.is_closing() is False:
                self.transport.close()
                self.on_con_lost.set_result(True)
        except Exception as e:
            self._print(e)

    def _keepalive(self):
        mesg = b"%maI"
        self.transport.write(mesg)
        self.mesg = None
        self._print("iAlarmMkPushClient - _keepalive, sent messagge:"+str(mesg))

    def _print(self, data):
        if self.logger is not None:
            self.logger.debug(str(data))
        else:
            print(str(data))

def BOL(en):
    if en == True:
        return "BOL|T"
    else:
        return "BOL|F"

def DTA(t):
    dta = time.strftime("%Y.%m.%d.%H.%M.%S", t)
    return "DTA,%d|%s" % (len(dta), dta)

def PWD(text):
    return "PWD,%d|%s" % (len(text), text)

def S32(val, pos=0):
    return "S32,%d,%d|%d" % (pos, pos, val)

def MAC(mac):
    return "MAC,%d|%d" % (len(mac), mac)

def IPA(ip):
    return "IPA,%d|%d" % (len(ip), ip)

def STR(text):
    text = str(text)
    return "STR,%d|%s" % (len(text), text)

def TYP(val, typ=[]):
    try:
        return "TYP,%s|%d" % (typ[val], val)
    except IndexError:
        return "TYP,NONE,|%d" % val

Cid = {
    "1100": "Personal ambulance",
    "1101": "Emergency",
    "1110": "Fire",
    "1120": "Emergency",
    "1131": "Perimeter",
    "1132": "Burglary",
    "1133": "24 hour",
    "1134": "Delay",
    "1137": "Dismantled",
    "1301": "System AC fault",
    "1302": "System battery failure",
    "1306": "Programming changes",
    "1350": "Communication failure",
    "1351": "Telephone line fault",
    "1370": "Circuit fault",
    "1381": "Detector lost",
    "1384": "Low battery detector",
    "1401": "Disarm report",
    "1406": "Alarm canceled",
    "1455": "Automatic arming failed",
    "1570": "Bypass Report",
    "1601": "Manual communication test reports",
    "1602": "Communications test reports",
    "3301": "System AC recovery",
    "3302": "System battery recovery",
    "3350": "Communication resumes",
    "3351": "Telephone line to restore",
    "3370": "Loop recovery",
    "3381": "Detector loss recovery",
    "3384": "Detector low voltage recovery",
    "3401": "Arming Report",
    "3441": "Staying Report",
    "3570": "Bypass recovery",
    "3456": "Parzial Report"
}

TZ = {
    0: "GMT-12:00",
    1: "GMT-11:00",
    2: "GMT-10:00",
    3: "GMT-09:00",
    4: "GMT-08:00",
    5: "GMT-07:00",
    6: "GMT-06:00",
    7: "GMT-05:00",
    8: "GMT-04:00",
    9: "GMT-03:30",
    10: "GMT-03:00",
    11: "GMT-02:00",
    12: "GMT-01:00",
    13: "GMT",
    14: "GMT+01:00",
    15: "GMT+02:00",
    16: "GMT+03:00",
    17: "GMT+04:00",
    18: "GMT+05:00",
    19: "GMT+05:30",
    20: "GMT+05:45",
    21: "GMT+06:00",
    22: "GMT+06:30",
    23: "GMT+07:00",
    24: "GMT+08:00",
    25: "GMT+09:00",
    26: "GMT+09:30",
    27: "GMT+10:00",
    28: "GMT+11:00",
    29: "GMT+12:00",
    30: "GMT+13:00",
}