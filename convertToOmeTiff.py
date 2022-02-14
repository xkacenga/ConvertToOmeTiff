#!/usr/bin/python3

import pyvips
import configparser
import xml.etree.ElementTree as ET
import argparse
import os


def main():
    args = parseArguments()
    if args.slide:
        convertSlide(args.input, args.output, args.quality)
    if args.directory:
        convertDirectory(args.input, args.output, args.quality)


def parseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="INPUT slide (directory) path")
    parser.add_argument("output", help="OUTPUT slide (directory) path")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-d", "--directory", action="store_true",
                       help="convert all slides in the INPUT directory and save them to OUTPUT directory")
    group.add_argument("-s", "--slide", action="store_true",
                       help="convert INPUT slide and save it as OUTPUT")
    parser.add_argument("-quality", default=75, type=int,
                        help="compression quality [1-100] (default = 75)")
    return parser.parse_args()

def convertSlide(inputPath, outputPath, quality):
    im = pyvips.Image.openslideload(inputPath)

    # openslide will add an alpha ... drop it
    if im.hasalpha():
        im = im[:-1]

    image_height = im.height
    image_bands = im.bands

    # set minimal OME metadata
    initialXml = f"""<?xml version="1.0" encoding="UTF-8"?>
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
                    SizeC="{image_bands}"
                    SizeT="1"
                    SizeX="{im.width}"
                    SizeY="{image_height}"
                    SizeZ="1"
                    Type="uint8">
            </Pixels>
        </Image>
    </OME>"""

    xmlRoot = ET.fromstring(initialXml)

    # retrieve original .mrxs metadata
    originalMetadata = {}
    slidedatPath = inputPath.rsplit('.', 1)[0] + '/Slidedat.ini'
    config = configparser.ConfigParser()
    config.read(slidedatPath, encoding='utf-8-sig')

    # merge ome-xml with original .mrxs metadata

    structuredAnnotations = ET.Element('StructuredAnnotations')
    counter = 0
    for (key, val) in config.items('GENERAL'):
        xmlAnnotation = ET.SubElement(structuredAnnotations, 'XMLAnnotation',
                                    ID='Annotation:' + str(counter),
                                    Namespace='openmicroscopy.org/OriginalMetadata')
        value = ET.SubElement(xmlAnnotation, 'Value')
        originalMetadata = ET.SubElement(value, 'OriginalMetadata')
        k = ET.SubElement(originalMetadata, 'Key')
        k.text = key
        v = ET.SubElement(originalMetadata, 'Value')
        v.text = val

        counter += 1

    xmlRoot.append(structuredAnnotations)
    xmlString = ET.tostring(xmlRoot, encoding='utf-8')


    # before we can modify an image (set metadata in this case), we must take a
    # private copy
    im = im.copy()
    im.set_type(pyvips.GValue.gint_type, "page-height", image_height)
    im.set_type(pyvips.GValue.gstr_type, "image-description", xmlString)


    quality = quality
    im.tiffsave(outputPath, compression="jpeg", tile=True,
                tile_width=256, tile_height=256,
                pyramid=True, Q=quality, subifd=True)


def convertDirectory(inputPath, outputPath, quality):
    if not os.path.isdir(inputPath):
        print(inputPath + " is not a directory!")
        return
    if not os.path.isdir(outputPath):
        print(outputPath + " is not a directory!")
        return
    directory = os.fsencode(inputPath)

    fileCount = 0
    for file in os.listdir(directory):
        fileName = os.fsdecode(file)
        if fileName.endswith(".mrxs"):
            fileCount += 1

    convertedCounter = 1
    for file in os.listdir(directory):
        fileName = os.fsdecode(file)
        baseFileName = os.path.splitext(fileName)[0]
        if fileName.endswith(".mrxs"):
            input = os.path.join(inputPath, fileName)
            output = os.path.join(outputPath, baseFileName + ".ome.tif")
            progressString = "[" + str(convertedCounter) + "/" + str(fileCount) + "]"
            if os.path.isfile(output):
                print(
                    baseFileName + ".ome.tif is already in the output directory. Skipping. "
                    + progressString)
            else:
                print("Converting " + fileName + " " + progressString)
                convertSlide(input, output, quality)
            convertedCounter += 1

    
    

if __name__ == "__main__":
    main()


