#!/usr/bin/python3

import pyvips
import configparser
import xml.etree.ElementTree as ET
import argparse

def main():
    args = parseArguments()
    if args.compression != "jpeg" and args.compression != "jp2k":
        print("Wrong compression type! Compression has to be 'jpeg' or 'jp2k'")
        return
    convertSlide(args.input, args.output, args.compression, args.quality)


def parseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="INPUT slide (directory) path")
    parser.add_argument("output", help="OUTPUT slide (directory) path")
    parser.add_argument("--quality", default=80, type=int,
                        help="compression quality [1-100] (default = 80)")
    parser.add_argument("--compression",  type=str,
                        help="compression ('jpeg' or 'jp2k')")
    return parser.parse_args()

def convertSlide(inputPath, outputPath, compression, quality):
    im = pyvips.Image.openslideload(inputPath)
    im = removeAlpha(im)
    omeXml = createOmeXml(inputPath, im)
    im = setImageMetadata(im, omeXml)
    
    im.tiffsave(outputPath, compression=compression, tile=True,
                tile_width=256, tile_height=256,
                pyramid=True, Q=quality, subifd=True) 

def createOmeXml(inputPath, im):
    xmlRoot = getMinimalOmeXmlRoot(im)
    metadataDict = extractMetadata(inputPath)
    omeXml = mergeXmlAndMetadata(xmlRoot, metadataDict)
    return omeXml

def setImageMetadata(im, omeXml):
    im = im.copy()
    im.set_type(pyvips.GValue.gint_type, "page-height", im.height)
    im.set_type(pyvips.GValue.gstr_type, "image-description", omeXml)
    return im

def removeAlpha(im):
    if im.hasalpha():
        im = im[:-1]
    return im

def getMinimalOmeXmlRoot(im):
    xmlStr = f"""<?xml version="1.0" encoding="UTF-8"?>
    <!-- Warning: this comment is an OME-XML metadata block, which contains
    crucial dimensional parameters and other important metadata. Please edit
    cautiously (if at all), and back up the original data before doing so.
    For more information, see the OME-TIFF documentation:
    https://docs.openmicroscopy.org/latest/ome-model/ome-tiff/ -->
    <OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.openmicroscopy.org/Schemas/OME/2016-06 http://www.openmicroscopy.org/Schemas/OME/2016-06/ome.xsd">
        <Image ID="Image:0">
            <Pixels DimensionOrder="XYCZT"
                    ID="Pixels:0"
                    SizeC="{im.bands}"
                    SizeT="1"
                    SizeX="{im.width}"
                    SizeY="{im.height}"
                    SizeZ="1"
                    Type="uint8">
            </Pixels>
        </Image>
    </OME>"""
    return ET.fromstring(xmlStr)
    
def extractMetadata(inputPath):
    slidedatPath = inputPath.rsplit('.', 1)[0] + '/Slidedat.ini'
    config = configparser.ConfigParser()
    config.read(slidedatPath, encoding='utf-8-sig')
    return dict(config['GENERAL'])

def mergeXmlAndMetadata(initialXmlRoot, metadataDict):
    structuredAnnotations = ET.Element('StructuredAnnotations')
    counter = 0
    for key, val in metadataDict.items():
        createAnnotation(structuredAnnotations, counter, key, val)
        counter += 1
    initialXmlRoot.append(structuredAnnotations)
    return ET.tostring(initialXmlRoot, encoding='utf-8')

def createAnnotation(structuredAnnotations, counter, key, val):
    xmlAnnotation = ET.SubElement(structuredAnnotations, 'XMLAnnotation',
                                    ID='Annotation:' + str(counter),
                                    Namespace='openmicroscopy.org/OriginalMetadata')
    value = ET.SubElement(xmlAnnotation, 'Value')
    originalMetadata = ET.SubElement(value, 'OriginalMetadata')
    k = ET.SubElement(originalMetadata, 'Key')
    k.text = key
    v = ET.SubElement(originalMetadata, 'Value')
    v.text = val

if __name__ == "__main__":
    main()


