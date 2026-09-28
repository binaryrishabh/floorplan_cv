import pymupdf

def open_doc(path):
    return pymupdf.open(path)

def page_drawings(page):
    return page.get_drawings()

def page_text_spans(page):
    out=[]
    raw=page.get_text('dict')
    for block in raw.get('blocks',[]):
        for line in block.get('lines',[]):
            for span in line.get('spans',[]):
                text=span.get('text','').strip()
                if not text:
                    continue
                x0,y0,x1,y1=span['bbox']
                out.append({
                    'text':text,
                    'bbox':(x0,y0,x1,y1),
                    'x':(x0+x1)/2.0,
                    'y':(y0+y1)/2.0,
                    'size':float(span.get('size',0.0) or 0.0),
                })
    return out
