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
        self._load_template()

    def _load_template(self):
        with open("./main.html") as template_f, \
                open("./menu.default") as menu_f, \
                open("./seed.default") as seed_f, \
                open("./ks.default") as ks_f:
            self.template = Environment().from_string(template_f.read()).render(MENU_ENTRIES=menu_f.read(),
                                                                                SEED_CONTENT=seed_f.read(),
                                                                                KS_CONTENT=ks_f.read(),
                                                                                ISOS=self.iso_selection)

    @cherrypy.expose
    def index(self, refresh=False):
        if refresh:
            self._load_template()
        yield(self.template)

    @cherrypy.expose
    def getIso(self, menu_entries, seed_content, kickstart, base_image):
        assert base_image in self.iso_selection

        cherrypy.response.headers['Content-Type'] = 'application/octet-stream'
        cherrypy.response.headers['Content-Description'] = 'File Transfer'
        cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="{}-custom.iso"'.format(base_image)

        builder = self.isoBuilder(menu_entries, seed_content, kickstart, base_image)
        return builder()
    getIso._cp_config = {'response.stream': True}

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

            print("Done!")
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
