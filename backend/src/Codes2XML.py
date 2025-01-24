import xml.etree.ElementTree as et

def generate_xml(bottle_codes: list[str], group_code: str) -> str:
    root = et.Element("codes")
    for code in bottle_codes:
        row = et.SubElement(root, "row")
        km = et.SubElement(row, "km")
        km.text = code
        ka = et.SubElement(row, "ka")
        ka.text = group_code
    return et.tostring(root, encoding="unicode", method="xml")