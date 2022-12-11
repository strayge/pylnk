from pylnk3.exceptions import FormatException


def guid_to_str(guid: bytes) -> str:
    ordered = [
        guid[3], guid[2], guid[1], guid[0],
        guid[5], guid[4], guid[7], guid[6],
        guid[8], guid[9], guid[10], guid[11],
        guid[12], guid[13], guid[14], guid[15],
    ]
    res = "{%02X%02X%02X%02X-%02X%02X-%02X%02X-%02X%02X-%02X%02X%02X%02X%02X%02X}" % tuple([x for x in ordered])
    # print(guid, res)
    return res


def guid_from_bytes(bytes: bytes) -> str:
    if len(bytes) != 16:
        raise FormatException(f"This is no valid _GUID: {bytes!s}")
    ordered = [
        bytes[3], bytes[2], bytes[1], bytes[0],
        bytes[5], bytes[4], bytes[7], bytes[6],
        bytes[8], bytes[9], bytes[10], bytes[11],
        bytes[12], bytes[13], bytes[14], bytes[15],
    ]
    return "{%02X%02X%02X%02X-%02X%02X-%02X%02X-%02X%02X-%02X%02X%02X%02X%02X%02X}" % tuple([x for x in ordered])


def bytes_from_guid(guid: str) -> bytes:
    nums = [
        guid[1:3], guid[3:5], guid[5:7], guid[7:9],
        guid[10:12], guid[12:14], guid[15:17], guid[17:19],
        guid[20:22], guid[22:24], guid[25:27], guid[27:29],
        guid[29:31], guid[31:33], guid[33:35], guid[35:37],
    ]
    ordered_nums = [
        nums[3], nums[2], nums[1], nums[0],
        nums[5], nums[4], nums[7], nums[6],
        nums[8], nums[9], nums[10], nums[11],
        nums[12], nums[13], nums[14], nums[15],
    ]
    return bytes([int(x, 16) for x in ordered_nums])
