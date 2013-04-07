#!/usr/bin/env python

# Copyright 2012 Gerwin Sturm, FoldedSoft e.U. / www.foldedsoft.at
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import json
import math
from argparse import ArgumentParser
from datetime import datetime


def main(argv):
    arg_parser = ArgumentParser()
    arg_parser.add_argument("input", help="Input File (JSON)")
    arg_parser.add_argument("output", help="Output File (will be overwritten!)")
    arg_parser.add_argument("-f", "--format", choices=["kml", "json", "csv", "js", "gpx"], default="kml", help="Format of the output")
    arg_parser.add_argument("-v", "--variable", default="latitudeJsonData", help="Variable name to be used for js output")
    args = arg_parser.parse_args()
    if args.input == args.output:
        arg_parser.error("Input and output have to be different files")
        return

    try:
        json_data = open(args.input).read()
    except:
        print("Error opening input file")
        return

    try:
        data = json.loads(json_data)
    except:
        print("Error decoding json")
        return

    if "data" in data and "items" in data["data"] and len(data["data"]["items"]) > 0:
        try:
            f_out = open(args.output, "w")
        except:
            print("Error creating output file for writing")
            return

        if args.format == "json" or args.format == "js":
            if args.format == "js":
                f_out.write("window.%s = " % args.variable)

            f_out.write("{\n")
            f_out.write("  \"data\": {\n")
            f_out.write("    \"items\": [\n")
            first = True
            items = data["data"]["items"]
            for item in items:
                if first:
                    first = False
                else:
                    f_out.write(",\n")
                f_out.write("      {\n")
                f_out.write("         \"timestampMs\": %s,\n" % item["timestampMs"])
                f_out.write("         \"latitude\": %s,\n" % item["latitude"])
                f_out.write("         \"longitude\": %s\n" % item["longitude"])
                f_out.write("      }")
            f_out.write("\n    ]\n")
            f_out.write("  }\n}")
            if args.format == "js":
                f_out.write(";")

        if args.format == "csv":
            f_out.write("Time,Location\n")
            items = data["data"]["items"]
            for item in items:
                f_out.write(datetime.fromtimestamp(int(item["timestampMs"]) / 1000).strftime("%Y-%m-%d %H:%M:%S"))
                f_out.write(",")
                f_out.write("%s %s\n" % (item["latitude"], item["longitude"]))

        if args.format == "kml":
            f_out.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            f_out.write("<kml xmlns=\"http://www.opengis.net/kml/2.2\">\n")
            f_out.write("  <Document>\n")
            f_out.write("    <name>Location History</name>\n")
            items = data["data"]["items"]
            for item in items:
                f_out.write("    <Placemark>\n")
                f_out.write("      <Point><coordinates>%s,%s</coordinates></Point>\n" % (item["longitude"], item["latitude"]))
                f_out.write("      <TimeStamp><when>")
                f_out.write(datetime.fromtimestamp(int(item["timestampMs"]) / 1000).strftime("%Y-%m-%dT%H:%M:%SZ"))
                f_out.write("</when></TimeStamp>\n")
                f_out.write("    </Placemark>\n")
            f_out.write("  </Document>\n</kml>\n")

        if args.format == "gpx":
            f_out.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            f_out.write("<gpx version=\"1.0\" creator=\"Google Latitude JSON Converter\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xmlns=\"http://www.topografix.com/GPX/1/0\" xsi:schemaLocation=\"http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd\">\n")
            f_out.write("  <trk>\n")
            f_out.write("    <name>Location History</name>\n")
            f_out.write("    <trkseg>\n")
            lastloc = None
            # Below assumes JSON input is in reverse chronological order.  If not, this will work better:
            # items = sorted(data["data"]["items"], key=lambda x: x['timestampMs'])
            items = reversed(data["data"]["items"])
            for item in items:
                if lastloc:
                    timedelta = (int(item['timestampMs']) - int(lastloc['timestampMs'])) / 1000 / 60
                    distancedelta = getDistanceFromLatLonInKm(item['latitude'], item['longitude'], lastloc['latitude'], lastloc['longitude'])
                    if timedelta > 10 or distancedelta > 40:
                        # No points for 10 minutes or 40km in under 10m? Start a new track.
                        f_out.write("    </trkseg>\n")
                        f_out.write("  </trk>\n")
                        f_out.write("  <trk>\n")
                        f_out.write("    <trkseg>\n")
                f_out.write("      <trkpt lat=\"%s\" lon=\"%s\">\n" % (item["latitude"], item["longitude"]))
                f_out.write("        <time>%s</time>\n" % str(datetime.fromtimestamp(int(item["timestampMs"]) / 1000).strftime("%Y-%m-%dT%H:%M:%SZ")))
                f_out.write("      </trkpt>\n")
                lastloc = item
            f_out.write("    </trkseg>\n")
            f_out.write("  </trk>\n")
            f_out.write("</gpx>\n")

        f_out.close()

    else:
        print("No data found in json")
        return


# Haversine formula
def getDistanceFromLatLonInKm(lat1,lon1,lat2,lon2):
    R = 6371 # Radius of the earth in km
    dlat = deg2rad(lat2-lat1)
    dlon = deg2rad(lon2-lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + \
    math.cos(deg2rad(lat1)) * math.cos(deg2rad(lat2)) * \
    math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c # Distance in km
    return d


def deg2rad(deg):
    return deg * (math.pi/180)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
