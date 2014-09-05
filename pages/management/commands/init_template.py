# XXX - Command need to be modified or delete

import os, random, string, re

from django.core.management.base import NoArgsCommand
from django.conf import settings

from bs4 import BeautifulSoup

from pages.models import PageElement

#pylint: disable=line-too-long

class Command(NoArgsCommand):
    help = 'Init PageElement for templates'

    def handle_noargs(self, **options):
		# print settings.TEMPLATE_DIRS
        for directory in settings.TEMPLATE_DIRS:
            for (dirpath, dirnames, filenames) in os.walk(directory): #pylint: disable=unused-variable
                for filename in filenames:
                    if filename.endswith('.html'):
                        changed = False
                        with open(os.path.join(dirpath, filename), "r") as myfile:
                            # print myfile.read()
                            soup = BeautifulSoup(myfile)
                            self.stdout.write("  Initialize %s ..." % os.path.join(dirpath, filename), ending="")
                            self.stdout.flush()
                            for editable in soup.find_all(class_="editable"):
                                try:
                                    # for now nothing to do if exists
                                    pagelement = PageElement.objects.get(
                                        slug__exact=editable['id'])
                                except:
                                    new_id = ''.join(random.choice(string.lowercase) for i in range(10))
                                    while PageElement.objects.filter(slug__exact=new_id).count() > 0:
                                        new_id = ''.join(random.choice(string.lowercase) for i in range(10))
                                    editable['id'] = new_id
                                    changed = True
                                    new_text = re.sub(r'[\ ]{2,}', '', editable.string)
                                    if new_text.startswith('\n'):
                                        new_text = new_text[1:]
                                    if new_text.endswith('\n'):
                                        new_text = new_text[:len(new_text)-1]
                                    pagelement = PageElement(slug=new_id, text=new_text)
                                    pagelement.save()
                                    html = soup.prettify("utf-8")
                        if changed:
                            self.stdout.write(" INIT OK")
                            with open(os.path.join(dirpath, filename), "w") as myfile:
                                myfile.write(html)
                        else:
                            self.stdout.write(" PASS")
