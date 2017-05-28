#!/bin/bash -ex

ISO_PATH="$1"
ISO_NAME="$(basename $1 | sed -E 's/\.iso$//' )"


mkdir iso_raws/$ISO_NAME
cd iso_raws/$ISO_NAME

bsdtar xfp $ISO_PATH

chmod 644 isolinux/txt.cfg isolinux/isolinux.bin
chmod 755 preseed/ .
