#!/usr/bin/env python3

import cherrypy
from jinja2 import Environment
from subprocess import Popen, PIPE
from threading import Semaphore
import os


class ISOserver(object):
    def __init__(self):
        self.data_dir = "./iso_raws"
        self.iso_selection = [i for i in os.listdir(self.data_dir) if not i.startswith(".")]
        self.builder_semaphores = {i: Semaphore() for i in self.iso_selection}
        self._load_templates()

    def _load_templates(self):
        with open("./main.html") as template_f:
            self.template = Environment().from_string(template_f.read())

        samples = os.listdir("samples")
        self.samples = {}

        for item in samples:
            self.samples[item] = {}
            with open(os.path.join("samples", item, "menu.default")) as f:
                self.samples[item]["MENU_ENTRIES"] = f.read()
            with open(os.path.join("samples", item, "seed.default")) as f:
                self.samples[item]["SEED_CONTENT"] = f.read()
            with open(os.path.join("samples", item, "ks.default")) as f:
                self.samples[item]["KS_CONTENT"] = f.read()
            info_path = os.path.join("samples", item, "info.txt")
            if os.path.exists(info_path):
                with open(os.path.join("samples", item, "info.txt")) as f:
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

    @cherrypy.expose
    def process(self, menu_entries, seed_content, kickstart, base_image, action, sample):
        assert base_image in self.iso_selection

        if action == "Load":
            assert sample in self.samples.keys()
            raise cherrypy.HTTPRedirect("/?base_image={}&sample={}".format(base_image, sample))

        elif action == "Build":
            cherrypy.response.headers['Content-Type'] = 'application/octet-stream'
            cherrypy.response.headers['Content-Description'] = 'File Transfer'
            cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="{}-custom.iso"'.format(base_image)

            builder = self.isoBuilder(menu_entries, seed_content, kickstart, base_image)
            return builder()
    process._cp_config = {'response.stream': True}

    def isoBuilder(self, menu_entries, seed_content, kickstart, base_image):
        datadir = os.path.join(self.data_dir, base_image)

        def output():
            self.builder_semaphores[base_image].acquire()

            with open(os.path.join(datadir, "isolinux/txt.cfg"), "w") as f:
                f.write(menu_entries)
            with open(os.path.join(datadir, "preseed/custom.seed"), "w") as f:
                f.write(seed_content)
            with open(os.path.join(datadir, "ks.cfg"), "w") as f:
                f.write(kickstart)

            try:
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
                self.builder_semaphores[base_image].release()
                raise
            else:
                self.builder_semaphores[base_image].release()

        return output


if __name__ == '__main__':

    cherrypy.config.update({
        'engine.autoreload_on': False,
        'tools.sessions.on': False,
        'tools.sessions.storage_type': 'ram',  # 'file',
        'tools.sessions.timeout': 525600,
        'server.show.tracebacks': True,
        'server.socket_port': 8087,
        'server.thread_pool': 10,
        'server.socket_host': '0.0.0.0',
        # 'tools.sessions.storage_path': './sessions/',
        'tools.sessions.locking': 'explicit'  # cherrypy.session.acquire_lock() cherrypy.session.release_lock()
    })

    cherrypy.tree.mount(ISOserver(), '/', config={
        '/': {},
        '/static': {  # 'tools.staticdir.on': True,
                      # 'tools.staticdir.dir': ./static/"
        }
    })
    cherrypy.engine.start()
    cherrypy.engine.block()
