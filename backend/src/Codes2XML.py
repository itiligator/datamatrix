import xml.etree.ElementTree as et
from io import StringIO


def generate_xml(bottle_codes: list[str], group_code: str) -> str:
    root = et.Element("codes")
    for code in bottle_codes:
        row = et.SubElement(root, "row")
        km = et.SubElement(row, "km")
        km.text = code
        ka = et.SubElement(row, "ka")
        ka.text = group_code

    tree = et.ElementTree(root)
    et.indent(tree, '  ')
    xml_buffer = StringIO()
    tree.write(xml_buffer, encoding="unicode", xml_declaration=True)
    return xml_buffer.getvalue()
