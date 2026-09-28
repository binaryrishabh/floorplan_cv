import pymupdf

class PageSpace:
    def __init__(self,page,dpi):
        self.page=page
        self.scale=dpi/72.0
        self.rotation_matrix=page.rotation_matrix
    def raw_to_pixel(self,x,y):
        p=pymupdf.Point(x,y)*self.rotation_matrix
        return p.x*self.scale,p.y*self.scale
