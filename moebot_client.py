
from pymoebot import MoeBot as PyMoeBot
import tinytuya
import logging
from typing import Dict, List, Tuple

_log = logging.getLogger("moebot_client")

class PasswordDecoder:
    """Decode device PIN from numeric to letter format"""
    
    # Mapping: 1=A, 2=B, 3=C, 4=D
    DIGIT_TO_LETTER = {
        '1': 'A',
        '2': 'B',
        '3': 'C',
        '4': 'D'
    }
    
    @staticmethod
    def decode(password_value: int) -> str:
        if password_value is None:
            return ""
        
        try:
            password_str = str(password_value)
            decoded = ""
            
            for digit in password_str:
                if digit in PasswordDecoder.DIGIT_TO_LETTER:
                    decoded += PasswordDecoder.DIGIT_TO_LETTER[digit]
                else:
                    decoded += digit
            
            return decoded
        except (ValueError, TypeError):
            return ""

class ErrorDecoder:
    """Decode MachineError bitmap (DPS 102) into individual error flags"""
    
    ERROR_CODES = {
        0: "FAULT_LEAN",
        1: "FAULT_TOO_STEEP",
        2: "NO_SIGNAL",
        3: "L_MOTOR_ERROR",
        4: "R_MOTOR_ERROR",
        5: "BATTERY_VOL_HIGH",
        6: "CHARGE_OVERCURRENT",
        7: "CHARGE_OVERVOLTAGE",
        8: "CHARGE_OVERTEMP",
        9: "BATTERY_DAMAGE",
        10: "BATTERY_LOW",
        11: "DISCHARGE_CURRENT",
        12: "DISCHARGE_TEMP",
        13: "UNEXPECTED_LOW",
        14: "EXPECTED_ERROR",
        15: "IMU_INVALID",
        16: "EMS_INVALID",
        17: "RAIN_INVALID",
        18: "HALL_INVALID",
        19: "STEEP_OVER_3S",
        20: "OUTSIDE_AREA",
        21: "LIFTED",
        22: "TRAPPED",
        23: "B_MOTOR_ERROR",
        24: "OVERTURN",
        25: "MOTOR_OVERCURRENT",
        26: "MOTOR_HALL",
        27: "MOTOR_DISCONNECT",
        28: "EMS_DISCONNECT",
        29: "MOTOR_ERROR"
    }
    
    @staticmethod
    def decode(error_value: int) -> List[str]:
        if not isinstance(error_value, int):
            try:
                error_value = int(error_value)
            except (ValueError, TypeError):
                return []
        
        active_errors = []
        for bit_position, error_name in ErrorDecoder.ERROR_CODES.items():
            if error_value & (1 << bit_position):
                active_errors.append(error_name)
        
        return active_errors

class MoeBotClient(PyMoeBot):
    """
    Streamlined MoeBot Client.
    Inherits from pymoebot.MoeBot and adds robust connection and extended local data access.
    """
    
    def __init__(self, device_id: str, device_ip: str, local_key: str) -> None:
        # Initialize connection using PyMoeBot logic first
        # But we will override the internal device to be more robust if needed
        super().__init__(device_id, device_ip, local_key)
        
        # Access the private device object from parent class (name mangling: _MoeBot__device)
        self._device = getattr(self, f"_MoeBot__device") 
        
        self.__ensure_connection()

    def __ensure_connection(self):
        """Try multiple protocol versions to ensure a valid connection"""
        versions_to_try = [3.4, 3.3]
        connected = False
        
        for version in versions_to_try:
            try:
                self._device.set_version(version)
                status = self._device.status()
                if 'dps' in status:
                    _log.info(f"Connected to MoeBot using protocol version {version}")
                    connected = True
                    # Let the parent class parse this initial payload to set up state
                    # Access private method _MoeBot__parse_payload
                    parse_method = getattr(self, f"_MoeBot__parse_payload")
                    parse_method(status)
                    break
            except Exception as e:
                _log.debug(f"Protocol version {version} failed: {e}")
        
        if not connected:
            _log.warning("Could not establish robust connection with expected protocol versions.")
            
    @property
    def machine_errors(self) -> List[str]:
        """Get decoded machine errors from DPS 102"""
        # Rely on parent class poll() or recent status, but we can also fetch directly if needed
        # Since pymoebot doesn't store dps 102 directly in a public prop, let's fetch from cached status or query
        try:
            # We can check the internal device dps cache if accessible, or just query status
            # For simplicity and reliability, getting status is safest for a property access on a client
            result = self._device.status()
            if 'dps' in result and '102' in result['dps']:
                return ErrorDecoder.decode(result['dps']['102'])
        except Exception as e:
            _log.error(f"Error getting machine errors: {e}")
        return []

    @property
    def password(self) -> Dict[str, str]:
        """Get device password (numeric and letter format) from DPS 106"""
        try:
            result = self._device.status()
            if 'dps' in result and '106' in result['dps']:
                numeric_pw = result['dps']['106']
                return {
                    "numeric": numeric_pw,
                    "letter": PasswordDecoder.decode(numeric_pw)
                }
        except Exception as e:
            _log.error(f"Error getting password: {e}")
        return {"numeric": None, "letter": ""}
