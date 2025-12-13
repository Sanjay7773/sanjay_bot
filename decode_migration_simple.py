import base64
import urllib.parse
import struct

# Migration URL (paste here)
# py decode_migration_simple.py 
# ok
migration_url = "otpauth-migration://offline?data=CkQKEC03tXOBXp54TLSHLBeG4fUSCFMxNTIwOTU4GgthbmdlbG9uZS5pbiABKAEwAkITYTYyMDRlMTc2NTEyNjkzMDIzNxACGAEgAA%3D%3D"

# Extract base64 data
parsed = urllib.parse.urlparse(migration_url)
data_b64 = urllib.parse.parse_qs(parsed.query)["data"][0]
raw = base64.b64decode(data_b64)


def read_varint(stream, offset):
    value = 0
    shift = 0
    while True:
        b = stream[offset]
        offset += 1
        value |= ((b & 0x7F) << shift)
        if not (b & 0x80):
            break
        shift += 7
    return value, offset


offset = 0
print("\n✔️ Decoded Accounts:\n")

while offset < len(raw):
    tag = raw[offset]
    offset += 1

    if tag == 0x0A:  # otp_parameters repeated field
        length, offset = read_varint(raw, offset)
        end = offset + length

        secret = None
        name = ""
        issuer = ""

        while offset < end:
            field_tag = raw[offset]
            offset += 1
            field_num = field_tag >> 3
            field_type = field_tag & 7

            if field_type == 2:  # length-delimited
                flen, offset = read_varint(raw, offset)
                data = raw[offset:offset + flen]
                offset += flen

                if field_num == 1:
                    secret = base64.b32encode(data).decode()
                elif field_num == 2:
                    name = data.decode()
                elif field_num == 3:
                    issuer = data.decode()

        print("Account Name:", name)
        print("Issuer:", issuer)
        print("SECRET (BASE32):", secret)
        print("-" * 40)

    else:
        # skip unknown fields
        if tag & 7 == 0:  # varint
            _, offset = read_varint(raw, offset)
        elif tag & 7 == 2:  # length-delimited
            length, offset = read_varint(raw, offset)
            offset += length
