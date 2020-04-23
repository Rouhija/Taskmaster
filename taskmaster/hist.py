class History:

    def __init__(self):
        self.hist = []
        self.curr = 0
        self.lim = 25
        self.first = True

    def get_up(self):
        try:
            if not self.first and self.curr < len(self.hist) - 1:
                self.curr += 1
            r = self.hist[self.curr]
            self.first = False
            return r
        except:
            return None
    
    def get_down(self):
        try:
            if not self.first and self.curr > 0:
                self.curr -= 1
            r = self.hist[self.curr]
            return r
        except:
            return None

    def add(self, s):
        self.hist.insert(0, s)
        self.curr = 0
        self.first = True
        if len(self.hist) > self.lim:
            del self.hist[-1]