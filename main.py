from collections import namedtuple
from enum import Enum, unique
from io import BytesIO
from PIL import Image
from zipfile import ZipFile
import argparse
# from gifmaker import makedelta


@unique
class DEVICES(Enum):
    MAKO = (768, 1270)


def zero_padded_number(padding, num):
    num = str(num)
    while len(num) < padding:
        num = "0" + num
    return num


def _count(gif):
    count = 0
    time = 0
    while True:
        try:
            gif.seek(gif.tell() + 1)
            time += gif.info["duration"]
            count += 1
        except EOFError:
            gif.seek(0)
            break
    time = time / count
    return count, time


def count_frames(gif):
    return _count(gif)[0]


def count_time(gif):
    return _count(gif)[1]


def extract_frames(gif):
    frame = Image.open(gif)
    nframes = count_frames(frame)
    imglist = []
    for frames in range(nframes + 1):
        frame.seek(frames)
        imglist.append(frame.copy())

    return imglist


Part = namedtuple("Part", "loop delay folder")


def make_desc_file(width, height, fps, parts):
    desc = ""

    desc += "{w} {h} {s}\n".format(w=width, h=height, s=fps)
    for p in parts:
        desc += "p {l} {d} {f}\n".format(l=p.loop, d=p.delay, f=p.folder)

    return desc


def scale_img(width, img):
    wpercent = (width / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))
    return img.resize((width, hsize), Image.ANTIALIAS)


def make_bootanimation(dim, gif, outfn=None, fps=None, fit=None):
    width, height = dim

    if outfn is None:
        outfn = "bootanimation.zip"

    z = ZipFile(outfn, mode="w")

    if fps is None:
        fps = 1000 / count_time(Image.open(gif))

    desc = make_desc_file(width, height, int(fps), [Part(0, 0, "part0")])
    z.writestr("desc.txt", desc)

    images = extract_frames(gif)
    padding = len(str(len(images)))
    for index, image in enumerate(images):

        # scale it
        if fit is not None:
            x = int(width * (fit / 100))
            image = scale_img(x, image)

        # background it
        background = Image.new("RGBA", (width, height))
        x = int((width / 2) - (image.size[0] / 2))
        y = int((height / 2) - (image.size[1] / 2))
        background.paste(image, (x, y))

        # save it
        img = BytesIO()
        background.save(img, format="png")
        z.writestr(
            'part0/{}.png'.format(zero_padded_number(padding, index)),
            img.getvalue()
        )

        # Technologic

    z.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Builds boot animations for android"
    )

    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser("list")

    preview_parser = subparsers.add_parser("preview")

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument(
        "dimensions",
        metavar="DIMENSIONS",
        help=(
            "name of a device listed by `list_devices` "
            "or a tuple containing width and height"
        )
    )
    build_parser.add_argument(
        "fname",
        metavar="FROM",
        help="the input GIF"
    )
    build_parser.add_argument(
        "-o",
        dest="outfilename",
        default="bootanimation",
        metavar="OUTPUT",
        help="name of the output zip file"
    )
    build_parser.add_argument(
        "--fps",
        default=None,
        type=int,
        help="speed of the animation"
    )
    build_parser.add_argument(
        "--fit",
        default=None,
        type=int,
        help="if set will upscale the animation to fit the dimensions"
    )

    args = parser.parse_args()

    if args.command == "list":
        for i in DEVICES:
            print(i)

    if args.command == "preview":
        print("[Insert preview here]")  # TODO

    if args.command == "build":
        args.dimensions = args.dimensions.upper()
        dimensions = device = None
        try:
            device = args.dimensions
            dimensions = DEVICES[args.dimensions].value
        except KeyError:
            device = "Unknown"
            dimensions = "".join(
                i for i in args.dimensions if i not in "() "
            ).split(",")

            try:
                dimensions = [int(i) for i in dimensions]
            except ValueError:
                err = "Invalid dimensions or device name ({})"
                raise Exception(err.format(args.dimensions))

        outfilename = args.outfilename
        if not outfilename.endswith(".zip"):
            outfilename += ".zip"

        print("Building animation for {device}{dimensions}".format(
            device=device, dimensions=dimensions))

        make_bootanimation(
            dimensions, args.fname, outfilename, args.fps, args.fit
        )

        print("Output in {}".format(outfilename))
