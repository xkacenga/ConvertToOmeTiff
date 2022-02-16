#!/usr/bin/env python3
  
import sys
import pyvips
import xml.etree.ElementTree as ET

def main():
    im = pyvips.Image.new_from_file(sys.argv[1])

    # openslide will add an alpha ... drop it
    if im.hasalpha():
        im = im[:-1]

    image_height = im.height
    image_bands = im.bands

    # split to separate image planes and stack vertically ready for OME 
    im = pyvips.Image.arrayjoin(im.bandsplit(), across=1)

    # set minimal OME metadata
    # before we can modify an image (set metadata in this case), we must take a 
    # private copy
    im = im.copy()
    im.set_type(pyvips.GValue.gint_type, "page-height", image_height)
    
    initialXml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.openmicroscopy.org/Schemas/OME/2016-06 http://www.openmicroscopy.org/Schemas/OME/2016-06/ome.xsd">
        <Image ID="Image:0">
            <Pixels DimensionOrder="XYCZT"
                    ID="Pixels:0"
                    SizeC="{image_bands}"
                    SizeT="1"
                    SizeX="{im.width}"
                    SizeY="{image_height}"
                    SizeZ="1"
                    Type="uint8">
                        <MetadataOnly/>
            </Pixels>
        </Image>
    </OME>"""

    inputFormat = sys.argv[1].rsplit(".", 1)[1]
    xml = createOmeXml(im, initialXml, inputFormat)
    im.set_type(pyvips.GValue.gstr_type, "image-description", xml)

    im.tiffsave(sys.argv[2], compression="jpeg", tile=True,
                tile_width=256, tile_height=256,
                pyramid=True, subifd=True)

def createOmeXml(im, initialXml, inputFormat):
    mdDict = extractMetadata(im, inputFormat)
    ET.register_namespace("OME", "http://www.openmicroscopy.org/Schemas/OME/2016-06")
    root = ET.fromstring(initialXml)
    structuredAnnotations = ET.SubElement(root, "OME:StructuredAnnotations")
    counter = 0
    for key, value in mdDict.items():
        xmlAnnotation = ET.SubElement(structuredAnnotations, "OME:XMLAnnotation")
        xmlAnnotation.set("ID", "Annotation:" + str(counter))
        counter += 1
        val = ET.SubElement(xmlAnnotation, "OME:Value")
        originalMetadata = ET.SubElement(val, "OriginalMetadata")
        k = ET.SubElement(originalMetadata, "Key")
        k.text = key
        v = ET.SubElement(originalMetadata, "Value")
        v.text = value
    return ET.tostring(root, encoding='utf-8')

def extractMetadata(im, inputFormat):
    mdDict = {}
    items = []
    if inputFormat == "mrxs":
        items = filter(lambda item: "mirax.GENERAL" in item, im.get_fields())
    elif inputFormat == "svs":
        items = filter(lambda item: "aperio." in item, im.get_fields())
    for item in items:
        key = item.rsplit(".", 1)[1]
        value = im.get(item)
        mdDict[key] = value
    return mdDict

if __name__ == "__main__":
    main()