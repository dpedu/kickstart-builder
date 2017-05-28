pip3 install -r requirements.txt
apt-get update && apt-get install -y genisoimage


To unpack ISOs:

apt-get install -y bsdtar

mkdir ubuntu-16.04.1-server-amd64
cd mkdir ubuntu-16.04.1-server-amd64
bsdtar xfp ../ubuntu-16.04.1-server-amd64.iso
chmod 644 isolinux/txt.cfg isolinux/isolinux.bin
chmod 755 preseed/ .
