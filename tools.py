def dist(x1, y1, x2, y2):
    return ((x1-x2)**2 + (y1-y2)**2) ** (1/2)

class Line:
    def __init__(self, m, b):
        self.m = m
        self.b = b

    def intersect(self, line):
        if self.m - line.m == 0:
            x = 100000000

        else:
            x = (line.b-self.b)/(self.m-line.m)
        y = self.m * x + self.b
        return x, y

    @classmethod
    def determineFromPoints(cls, x1, y1, x2, y2):
        if (x2-x1) == 0:
            slope = 1000000
        
        else:
            slope = (y2-y1)/(x2-x1)
        
        b = y1 - x1*slope
        return Line(slope, b)

    @classmethod
    def determineFromSlopePoint(cls, m, x1, y1):
        slope = m

        b = y1 - x1*slope
        return Line(slope, b)

    def getPointAt(self, x):
        return self.m * x + self.b

    def __repr__(self):
        return f"y={self.m}x+{self.b}"