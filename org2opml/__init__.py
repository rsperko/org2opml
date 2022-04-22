import re
import xml.etree.ElementTree as ET
import argparse
from typing import Set

from orgparse import load, OrgNode


TODO_TYPES = ['TODO ', 'ACTIVE ', 'WAITING ', 'DONE ', 'WONT ']
DONE_TYPES = ['DONE ', 'WONT ']


def _apply_heading(xml_node: ET.Element, heading: str):
    if not heading:
        return

    for todo_type in TODO_TYPES:
        if heading.startswith(todo_type):
            xml_node.attrib["checkbox"] = "true"
            if todo_type in DONE_TYPES:
                xml_node.attrib["complete"] = "true"
            heading = heading[len(todo_type):]
            break
    xml_node.attrib["text"] = heading


def _entire_body_is_list(body: str):
    content = body.strip()
    p = re.compile(r'\s*- ')
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        if not p.match(line):
            return False
    return True


def _append_body_list(xml_node: ET.Element, body: str):
    content = body.strip()
    p = re.compile(r'(\s*)- (\[.\] )?(.*)')

    parents = {0: xml_node}

    for line in content.split("\n"):
        line = line.rstrip()
        if not line:
            continue
        parts = p.match(line)
        spaces = parts.group(1)
        todo = parts.group(2)
        body = parts.group(3)
        level = len(spaces) / 2
        complete = todo == '[X] '

        attribs = dict(text=body)
        if todo:
            attribs["checkbox"] = "true"
            if complete:
                attribs["complete"] = "true"

        list_node = ET.SubElement(parents[level], "outline", attrib=attribs)
        parents[level+1] = list_node


def _apply_body(xml_node: ET.Element, body: str):
    if not body:
        return

    if _entire_body_is_list(body):
        _append_body_list(xml_node, body)
    else:
        xml_node.attrib["_note"] = body


def _append_tags(xml_node: ET.Element, tags: Set[str]):
    text = xml_node.attrib.get("text", "")

    for tag in tags:
        text += f" #{tag}"

    if text:
        xml_node.attrib["text"] = text


def _apply_todo(xml_node, todo):
    if todo:
        xml_node.attrib["checkbox"] = "true"
        if todo == "DONE":
            xml_node.attrib["complete"] = "true"


def _apply_priority(xml_node, priority):
    if priority:
        text = xml_node.attrib.get("text", "") + f" #{priority}"
        xml_node.attrib["text"] = text


def _add_node(parent: ET.Element, org_node: OrgNode):
    if not org_node.heading and not org_node.children:
        return

    xml_node = ET.SubElement(parent, "outline", attrib=dict())

    _apply_heading(xml_node, org_node.heading)
    _apply_todo(xml_node, org_node.todo)
    _apply_body(xml_node, org_node.body)
    _append_tags(xml_node, org_node.tags)
    _apply_priority(xml_node, org_node.priority)

    for child_node in org_node.children:
        _add_node(xml_node, child_node)


def _main(org_filename: str):
    root = load(org_filename)

    opml = ET.Element("opml", attrib={"version": "2.0"})
    head = ET.SubElement(opml, "head")
    body = ET.SubElement(opml, "body")
    for node in root.children:
        _add_node(body, node)

    xml = ET.ElementTree(opml)
    ET.indent(xml, space="\t", level=0)
    xml.write(org_filename + ".opml", xml_declaration=True, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert org file to opml file")
    parser.add_argument("orgfile", help="org-mode file to read and convert")

    args = parser.parse_args()
    _main(args.orgfile)
