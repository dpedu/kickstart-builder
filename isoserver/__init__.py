#!/usr/bin/env python3

import cherrypy
from jinja2 import Environment
from subprocess import Popen, PIPE
from threading import Semaphore
import os


APPROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))


class ISOserver(object):
    def __init__(self, isodir):
        self.data_dir = isodir
        self.iso_selection = [i for i in os.listdir(self.data_dir) if not any([i.startswith("."), i == "samples"])]
        if not self.iso_selection:
            raise Exception("No base isos found in path {}".format(self.data_dir))

        self.builder_semaphores = {i: Semaphore() for i in self.iso_selection}
        self._load_templates()

    def _load_templates(self):
        with open(os.path.join(APPROOT, "main.html")) as template_f:
            self.template = Environment(autoescape=True).from_string(template_f.read())

        basedir = os.path.join(self.data_dir, "samples")
        os.makedirs(basedir, exist_ok=True)
        samples = os.listdir(basedir)
        if not samples:
            raise Exception("No templates found in path {}".format(basedir))
        self.samples = {}

        for item in samples:
            self.samples[item] = {}
            with open(os.path.join(basedir, item, "menu.default")) as f:
                self.samples[item]["MENU_ENTRIES"] = f.read()
            with open(os.path.join(basedir, item, "seed.default")) as f:
                self.samples[item]["SEED_CONTENT"] = f.read()
            with open(os.path.join(basedir, item, "ks.default")) as f:
                self.samples[item]["KS_CONTENT"] = f.read()
            info_path = os.path.join(basedir, item, "info.txt")
            if os.path.exists(info_path):
                with open(os.path.join(basedir, item, "info.txt")) as f:
                    self.samples[item]["SAMPLE_INFO"] = f.read()

    @cherrypy.expose
    def index(self, refresh=False, sample="default", base_image=""):
        if refresh or "REFRESH" in os.environ:
            self._load_templates()

        yield(self.template.render(ISOS=self.iso_selection,
                                   SAMPLES=self.samples.keys(),
                                   CURRENT_SAMPLE=sample,
                                   BASE_IMAGE=base_image,
                                   **self.samples[sample]))

    # @cherrypy.tools.noBodyProcess()
    @cherrypy.expose
    def process(self, menu_entries, seed_content, kickstart, base_image, action, sample, userdata):
        assert base_image in self.iso_selection

        if action == "Load":
            assert sample in self.samples.keys()
            raise cherrypy.HTTPRedirect("/?base_image={}&sample={}".format(base_image, sample))

        elif action == "Build":
            cherrypy.response.headers['Content-Type'] = 'application/octet-stream'
            cherrypy.response.headers['Content-Description'] = 'File Transfer'
            cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="{}-custom.iso"'.format(base_image)

            builder = self.isoBuilder(menu_entries, seed_content, kickstart, base_image, userdata)
            return builder()
    process._cp_config = {'response.stream': True}

    def isoBuilder(self, menu_entries, seed_content, kickstart, base_image, userdata):
        datadir = os.path.join(self.data_dir, base_image)

        userdata_path = None

        if userdata.file:
            userdata_name = os.path.basename(userdata.filename)
            userdata_path = os.path.join(datadir, userdata_name)
            if os.path.exists(userdata_path):
                raise Exception("File {} already exists".format(userdata_name))

        def output():
            self.builder_semaphores[base_image].acquire()

            with open(os.path.join(datadir, "isolinux/txt.cfg"), "w") as f:
                f.write(menu_entries)
            with open(os.path.join(datadir, "preseed/custom.seed"), "w") as f:
                f.write(seed_content)
            with open(os.path.join(datadir, "ks.cfg"), "w") as f:
                f.write(kickstart)

            try:
                if userdata.file:
                    with open(userdata_path, "wb") as f:
                        while True:
                            data = userdata.file.read(8192)
                            if not data:
                                break
                            f.write(data)

                proc = Popen(['/usr/bin/mkisofs', '-b', 'isolinux/isolinux.bin', '-c', 'isolinux/boot.cat',
                              '-no-emul-boot', '-boot-load-size', '4', '-boot-info-table', '-J', '-R', '-V',
                              'kickstart_linux', '.'], stdout=PIPE, cwd=datadir)
                with proc.stdout as f:
                    while True:
                        data = f.read(8192)
                        if not data:
                            break
                        yield data
            except Exception as e:
                raise
            finally:
                if userdata_path:
                    try:
                        os.unlink(userdata_path)
                    except FileNotFoundError:
                        pass
                self.builder_semaphores[base_image].release()

        return output


def main():
    from argparse import ArgumentParser
    import logging
    logging.basicConfig(level=logging.DEBUG)
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", help="listen port", default=int(os.environ.get("PORT", 8087)))
    parser.add_argument("-d", "--data", help="iso data folder", default=os.environ.get("DATADIR", "/data"))
    args = parser.parse_args()

    cherrypy.tree.mount(ISOserver(args.data), '/', config={})

    cherrypy.config.update({
        'environment': 'production',
        'server.socket_host': '0.0.0.0',
        'server.socket_port': args.port,
        'tools.sessions.on': False,
        'server.thread_pool': 10,
    })

    cherrypy.engine.start()
    cherrypy.engine.block()


if __name__ == '__main__':
    main()
