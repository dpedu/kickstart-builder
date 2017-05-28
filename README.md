kickstart-builder
=================

Automated ISO builder for kickstart-based installation CDs

Setup:
-----

* Clone the repo
* Install requirements:
  * `pip3 install -r requirements.txt`
  * `apt-get install -y bsdtar genisoimage`
* Prepare at least one ISO (see below)
* Start it
  * `python3 main.py`
* In your browser, visit http://127.0.0.1:8087/

Adding ISOs
-----------

For each ISO you want to make available, create a subdirectory under iso_raws with a name matching you want to see in
the UI. Unpack the contents of an ISO into this directory. Some files and directories will need to be chmodded so they
can be written to. Refer to the example commands below:


```
cd iso_raws
mkdir ubuntu-16.04.1-server-amd64
cd ubuntu-16.04.1-server-amd64
bsdtar xfp ~/Downloads/ubuntu-16.04.1-server-amd64.iso
chmod 644 isolinux/txt.cfg isolinux/isolinux.bin
chmod 755 preseed/ .
```

Alternatively, the script `add-iso.sh` can be used to add an ISO:

```
./add-iso.sh ~/Downloads/ubuntu-16.04.1-server-amd64.iso
```

Development Tips
----------------

In normal operation, the application loads templates and configs once on startup. If the `REFRESH` environmental
variable is set, it will reload the templates and configs on every page load:

```
REFRESH=1 python3 main.py
```

Additional config templates can be added under the "samples" directory.


Installing the `system-config-kickstart` provides a tool for generating Kickstart configs:

```
apt-get install system-config-kickstart
system-config-kickstart
```
