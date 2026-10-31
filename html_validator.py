import re
from html.parser import HTMLParser
from html_renderer import safe_local_href

ALLOWED_TAGS = {'html','head','body','meta','title','style','header','nav','main','section','article','footer','div','h1','h2','h3','h4','h5','h6','p','span','a','strong','em','ul','ol','li','br','hr'}
VOID = {'meta','br','hr'}
ALLOWED_CLASS = re.compile(r'[A-Za-z][A-Za-z0-9_-]*\Z')

class _Checker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.css = False
    def handle_starttag(self, name, attrs):
        if name not in ALLOWED_TAGS:
            self.errors.append('Forbidden tag: ' + name)
        attrs = dict(attrs)
        allowed = {'class'}
        if name == 'html': allowed |= {'lang'}
        if name == 'nav': allowed |= {'aria-label'}
        if name == 'a': allowed |= {'href'}
        if name == 'meta': allowed |= {'charset','name','content'}
        for k,v in attrs.items():
            if k not in allowed:
                self.errors.append('Forbidden attribute: ' + name + '.' + k)
            if k == 'class' and any(not ALLOWED_CLASS.fullmatch(s) for s in (v or '').split()):
                self.errors.append('Invalid class')
        if name == 'meta':
            charset = attrs == {'charset':'UTF-8'}
            viewport = attrs == {'name':'viewport','content':'width=device-width, initial-scale=1'}
            if not (charset or viewport): self.errors.append('Disallowed meta element')
        if name == 'a' and safe_local_href(attrs.get('href')) is None:
            self.errors.append('Unsafe link')
        if name == 'style': self.css = True
        if name not in VOID: self.stack.append(name)
    def handle_endtag(self, name):
        if name in VOID: self.errors.append('Unexpected closing void tag: '+name)
        elif not self.stack or self.stack[-1] != name:
            self.errors.append('Mismatched closing tag: '+name)
        else:
            self.stack.pop()
        if name == 'style': self.css = False
    def handle_data(self, data):
        if self.css and re.search(r'@import|@font-face|url\s*\(|expression\s*\(|@namespace|image-set\s*\(|-moz-binding|behavior\s*:',data,re.I):
            self.errors.append('Disallowed CSS feature')


def validate_html(html):
    if not isinstance(html,str) or not html.strip(): return {'valid':False,'errors':['HTML is empty']}
    errors=[]
    if len(html) > 100_000: errors.append('HTML too long')
    if not re.match(r'\s*<!doctype\s+html\s*>',html,re.I): errors.append('Missing doctype')
    parser=_Checker()
    try:
        parser.feed(html)
        parser.close()
    except Exception as e:
        errors.append('Parser exception: '+str(e))
    errors += parser.errors
    if parser.stack: errors.append('Unclosed tags: '+', '.join(parser.stack))
    if not re.search(r'<body\b',html,re.I): errors.append('Missing body')
    return {'valid':not errors,'errors':list(dict.fromkeys(errors))}
