#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Script to generate backtest data in CSV format.
# Example usage:
#  ./fx-data-generate.py -s 10 -p random -v 100 2014.01.01 2014.01.30 2.0 4.0 | gnuplot -p -e "set datafile separator ','; plot '-' using 3 w l"

from __future__ import print_function
import argparse
import sys
import datetime
import csv
import random
from math import ceil, exp, pi, sin


def msg(*args, **kwargs):
    print("[INFO]", *args, file=sys.stderr, **kwargs)


def error(*args, **kwargs):
    print("[ERROR]", *args, file=sys.stderr, **kwargs)
    if exit:
        sys.exit(1)


def volumesFromTimestamp(timestamp, spread):
    longTimestamp = timestamp.timestamp()
    spread *= 1e5
    d = int(str(int(longTimestamp / 60))[-3:]) + 1
    bidVolume = int((longTimestamp / d) % (1e3 - spread))

    return (bidVolume, bidVolume + spread)


def linearModel(startDate, endDate, startPrice, endPrice, deltaTime, spread):
    timestamp = startDate
    bidPrice = startPrice
    askPrice = bidPrice + spread
    bidVolume = 1
    askVolume = bidVolume + spread
    deltaPrice = (
        deltaTime
        / (endDate + datetime.timedelta(days=1) - startDate - deltaTime)
        * (endPrice - startPrice)
    )
    ticks = []
    while timestamp < (endDate + datetime.timedelta(days=1)):
        ticks += [
            {
                "timestamp": timestamp,
                "bidPrice": bidPrice,
                "askPrice": askPrice,
                "bidVolume": bidVolume,
                "askVolume": askVolume,
            }
        ]
        timestamp += deltaTime
        bidPrice += deltaPrice
        askPrice += deltaPrice
        (bidVolume, askVolume) = volumesFromTimestamp(timestamp, spread)
    return ticks


def zigzagModel(
    startDate, endDate, startPrice, endPrice, deltaTime, spread, volatility
):
    timestamp = startDate
    bidPrice = startPrice
    askPrice = bidPrice + spread
    bidVolume = 1
    askVolume = bidVolume + spread
    deltaPrice = endPrice - startPrice
    count = ceil((endDate + datetime.timedelta(days=1) - startDate) / deltaTime)
    lift = deltaPrice / count
    forward = 500
    backward = int(volatility * 50)
    ticks = []
    # Calculate zigzag body
    for i in range(0, count - backward):
        ticks += [
            {
                "timestamp": timestamp,
                "bidPrice": bidPrice,
                "askPrice": askPrice,
                "bidVolume": bidVolume,
                "askVolume": askVolume,
            }
        ]
        i += 1
        timestamp += deltaTime
        if i % (forward + backward) < forward:
            bidPrice += (forward + 2 * backward) / forward * lift
        else:
            bidPrice -= lift
        askPrice = bidPrice + spread
        (bidVolume, askVolume) = volumesFromTimestamp(timestamp, spread)

    # Calculate tail as a linear line
    lift = (endPrice - bidPrice) / (backward - 1)
    for i in range(count - backward, count):
        ticks += [
            {
                "timestamp": timestamp,
                "bidPrice": bidPrice,
                "askPrice": askPrice,
                "bidVolume": bidVolume,
                "askVolume": askVolume,
            }
        ]
        i += 1
        timestamp += deltaTime
        bidPrice += lift
        askPrice = bidPrice + spread
        (bidVolume, askVolume) = volumesFromTimestamp(timestamp, spread)
    return ticks


def waveModel(startDate, endDate, startPrice, endPrice, deltaTime, spread, volatility):
    timestamp = startDate
    bidPrice = startPrice
    askPrice = bidPrice + spread
    bidVolume = 1
    askVolume = bidVolume + spread
    deltaPrice = endPrice - startPrice
    count = ceil((endDate + datetime.timedelta(days=1) - startDate) / deltaTime)
    d = count / 2  # Denominator for curve shaping
    ticks = []
    for i in range(0, count):
        ticks += [
            {
                "timestamp": timestamp,
                "bidPrice": bidPrice,
                "askPrice": askPrice,
                "bidVolume": bidVolume,
                "askVolume": askVolume,
            }
        ]
        i += 1
        timestamp += deltaTime
        # Select appropriate formula depending on starting and ending prices
        if abs(deltaPrice) > 0:
            bidPrice = abs(
                startPrice
                + i / (count - 1) * deltaPrice
                + volatility * sin(i / (count - 1) * 3 * pi)
            )
        else:
            bidPrice = abs(startPrice + (volatility * sin(i / (count - 1) * 3 * pi)))
        askPrice = bidPrice + spread
        (bidVolume, askVolume) = volumesFromTimestamp(timestamp, spread)
    return ticks


def curveModel(startDate, endDate, startPrice, endPrice, deltaTime, spread, volatility):
    timestamp = startDate
    bidPrice = startPrice
    askPrice = bidPrice + spread
    bidVolume = 1
    askVolume = bidVolume + spread
    deltaPrice = endPrice - startPrice
    count = ceil((endDate + datetime.timedelta(days=1) - startDate) / deltaTime)
    d = count / volatility  # A kind of volatility interpretation via curve shaping
    ticks = []
    for i in range(0, count):
        ticks += [
            {
                "timestamp": timestamp,
                "bidPrice": bidPrice,
                "askPrice": askPrice,
                "bidVolume": bidVolume,
                "askVolume": askVolume,
            }
        ]
        i += 1
        timestamp += deltaTime
        bidPrice = (
            startPrice
            + (1 - (exp(i / d) - exp((count - 1) / d)) / (1 - exp((count - 1) / d)))
            * deltaPrice
        )
        askPrice = bidPrice + spread
        (bidVolume, askVolume) = volumesFromTimestamp(timestamp, spread)
    return ticks


def randomModel(
    startDate, endDate, startPrice, endPrice, deltaTime, spread, volatility
):
    timestamp = startDate
    bidPrice = startPrice
    askPrice = bidPrice + spread
    bidVolume = 1
    askVolume = bidVolume + spread
    deltaPrice = (
        deltaTime
        / (endDate + datetime.timedelta(days=1) - startDate - deltaTime)
        * (endPrice - startPrice)
    )
    count = ceil((endDate + datetime.timedelta(days=1) - startDate) / deltaTime)
    ticks = []
    for i in range(0, count):
        ticks += [
            {
                "timestamp": timestamp,
                "bidPrice": bidPrice,
                "askPrice": askPrice,
                "bidVolume": bidVolume,
                "askVolume": askVolume,
            }
        ]
        timestamp += deltaTime
        bidPrice += deltaPrice + deltaPrice * (random.random() - 0.5) * volatility
        askPrice = bidPrice + spread
        (bidVolume, askVolume) = volumesFromTimestamp(timestamp, spread)
    ticks[-1]["bidPrice"] = endPrice
    ticks[-1]["askPrice"] = endPrice + spread
    return ticks


def toCsv(rows, digits, output):
    csvWriter = csv.writer(
        output, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
    )
    for row in rows:
        csvWriter.writerow(
            [
                row["timestamp"].strftime("%Y.%m.%d %H:%M:%S.%f")[:-3],
                ("{:.%df}" % (digits)).format(max(row["bidPrice"], 10 ** -digits)),
                ("{:.%df}" % (digits)).format(max(row["askPrice"], 10 ** -digits)),
                ("{:.%df}" % (digits)).format(row["bidVolume"]),
                ("{:.%df}" % (digits)).format(row["askVolume"]),
            ]
        )


if __name__ == "__main__":
    argumentParser = argparse.ArgumentParser()
    argumentParser.add_argument(
        "startDate", help="Starting date of generated data in YYYY.MM.DD format."
    )
    argumentParser.add_argument(
        "endDate", help="Ending date of generated data in YYYY.MM.DD format."
    )
    argumentParser.add_argument(
        "startPrice",
        type=float,
        help="Starting bid price of generated data, must be a float value.",
    )
    argumentParser.add_argument(
        "endPrice",
        type=float,
        help="Ending bid price of generated data, must be a float value.",
    )
    argumentParser.add_argument(
        "-D",
        "--digits",
        type=int,
        action="store",
        dest="digits",
        help="Decimal digits of prices.",
        default=5,
    )
    argumentParser.add_argument(
        "-s",
        "--spread",
        type=int,
        action="store",
        dest="spread",
        help="Spread between prices in points.",
        default=10,
    )
    argumentParser.add_argument(
        "-d",
        "--density",
        type=int,
        action="store",
        dest="density",
        help="Data points per minute in generated data.",
        default=1,
    )
    argumentParser.add_argument(
        "-p",
        "--pattern",
        action="store",
        dest="pattern",
        choices=["none", "wave", "curve", "zigzag", "random"],
        help="Modeling pattern, all of them are deterministic except of 'random'.",
        default="none",
    )
    argumentParser.add_argument(
        "-V",
        "--volatility",
        type=float,
        action="store",
        dest="volatility",
        help="Volatility factor (higher values leads to higher volatility in price values).",
        default=1.0,
    )
    argumentParser.add_argument(
        "-o",
        "--outputFile",
        action="store",
        dest="outputFile",
        help="Write generated data to file instead of standard output.",
    )
    argumentParser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        dest="verbose",
        help="Sets the verbosity logging level",
    )
    args = argumentParser.parse_args()

    # Check date values.
    try:
        startDate = datetime.datetime.strptime(args.startDate, "%Y.%m.%d")
        endDate = datetime.datetime.strptime(args.endDate, "%Y.%m.%d")
    except ValueError as e:
        error("Bad date format!")

    if endDate < startDate:
        error("Ending date precedes starting date!")

    if args.digits <= 0:
        error("Digits must be larger than zero!")

    if args.startPrice <= 0 or args.endPrice <= 0:
        error("Price must be larger than zero!")

    if args.spread < 0:
        error("Spread must be larger or equal to zero!")

    if args.density <= 0:
        error("Density must be larger than zero!")

    if args.volatility <= 0:
        error("Volatility must be larger than zero!")

    spread = args.spread / 1e5
    if args.verbose:
        msg("[INFO] Spread: %.2f" % spread)

    # Select and run appropriate model.
    deltaTime = datetime.timedelta(seconds=60 / args.density)
    if args.verbose:
        msg("[INFO] Pattern: %s" % args.pattern)
    rows = None
    if args.pattern == "none":
        rows = linearModel(
            startDate, endDate, args.startPrice, args.endPrice, deltaTime, spread
        )
    elif args.pattern == "zigzag":
        rows = zigzagModel(
            startDate,
            endDate,
            args.startPrice,
            args.endPrice,
            deltaTime,
            spread,
            args.volatility,
        )
    elif args.pattern == "wave":
        rows = waveModel(
            startDate,
            endDate,
            args.startPrice,
            args.endPrice,
            deltaTime,
            spread,
            args.volatility,
        )
    elif args.pattern == "curve":
        rows = curveModel(
            startDate,
            endDate,
            args.startPrice,
            args.endPrice,
            deltaTime,
            spread,
            args.volatility,
        )
    elif args.pattern == "random":
        rows = randomModel(
            startDate,
            endDate,
            args.startPrice,
            args.endPrice,
            deltaTime,
            spread,
            args.volatility,
        )
    if args.verbose:
        msg("[INFO] Generated rows: %d" % len(rows))

    # Output array stdout/file.
    if args.outputFile:
        if args.verbose:
            msg("[INFO] Output file: %s" % args.outputFile)
        with open(args.outputFile, "w") as outputFile:
            toCsv(rows, args.digits, outputFile)
    else:
        toCsv(rows, args.digits, sys.stdout)
