import sys
import re
from math import ceil, sin, cos, pi
from affine import Affine

def mm(m):
    return m/25.4

class GCodeWriter(object):
    def __init__(self, dryrun=False):
        self.dryrun = dryrun
        self.safe_z = 0.1
        self.delta_z = -0.02
        self.thickness = -0.125
        if self.dryrun:
            self.repeat = 1
        else:
            self.repeat = int(ceil(self.thickness / self.delta_z))
        self.plunge_rate = 1
        self.feed_rate = 5
        self.finish_cut = .005
        self.finish_depth = self.thickness - .05
        self.tool_diameter = 0.125
        self.tool_radius = self.tool_diameter / 2
        self.code = []

    def circle(self, x, y, radius):
        self.safez()
        roughadj = self.tool_radius + self.finish_cut
        self.rapid(x=x-radius+roughadj, y=y)
        z = 0
        for r in range(0, self.repeat):
            self.zfeed(z)
            # G91.1 = incremental IJ
            # G17 XY plane
            # Pn - this many full circles
            self.out("F%f G91.1 G17 G02 X%f Y%f I%f J%f Z%f" % (
                self.feed_rate,
                x-radius+roughadj, y,
                radius-roughadj, 0,
                z + self.delta_z))
            z += self.delta_z

        if not self.dryrun:
            finish = self.tool_radius
            self.feed(x=x-radius+roughadj, y=y)
            self.zfeed(self.finish_depth)
            self.feed(x=x-radius+finish, y=y)
            self.out("F%f G91.1 G17 G02 X%f Y%f I%f J%f" % (
                self.feed_rate,
                x-radius+finish, y,
                radius-finish, 0))
            self.feed(x=x-radius+roughadj, y=y)
        self.safez()


        #g.oval(-0.250, -0.250,  -0.375, -0.250, 0.125)

    def oval(self, x1, y1, x2, y2, radius):
        if y1 != y1:
            raise Exception("I only know how to make ovals where y1=y2")
        if x1 > x2:
            x1, x2 = x2, x1
        self.safez()
        roughrad = radius - self.tool_radius - self.finish_cut
        self.rapid(x=x1, y=y1-roughrad)
        z = self.delta_z
        for r in range(0, self.repeat):
            self.zfeed(z)
            # first draw leftmost arc centered on x1, y1
            self.out("F%f G91.1 G17 G02 X%f Y%f I%f J%f" % (
                self.feed_rate,
                x1, y1+roughrad,
                0, roughrad))
            # now line segment from x1, y1-radius
            self.out("F%f G1 X%f" % (self.feed_rate, x2))
            # now rightmost arc from x2, y1-radius
            self.out("F%f G91.1 G17 G02 X%f Y%f I%f J%f" % (
                self.feed_rate,
                x2, y1-roughrad,
                0, -roughrad))
            # now line segment from x2, y1+radius
            self.out("F%f G1 X%f" % (self.feed_rate, x1))
            z += self.delta_z
        if not self.dryrun:
            finrad = radius - self.tool_radius
            self.zfeed(self.finish_depth)
            self.feed(y=y1-finrad)
            # first draw leftmost arc centered on x1, y1
            self.out("F%f G91.1 G17 G02 X%f Y%f I%f J%f" % (
                self.feed_rate,
                x1, y1+finrad,
                0, finrad))
            # now line segment from x1, y1-radius
            self.out("F%f G1 X%f" % (self.feed_rate, x2))
            # now rightmost arc from x2, y1-radius
            self.out("F%f G91.1 G17 G02 X%f Y%f I%f J%f" % (
                self.feed_rate,
                x2, y1-finrad,
                0, -finrad))
            # now line segment from x2, y1+radius
            self.out("F%f G1 X%f" % (self.feed_rate, x1))
        self.safez()
        

    def safez(self):
        self.rapid(z=self.safe_z)

    def kwcoord(self, kwargs):
        o = ""
        if "x" in kwargs:
            o += "X%f" % (kwargs["x"])
        if "y" in kwargs:
            o += "Y%f" % (kwargs["y"])
        if "z" in kwargs:
            o += "Z%f" % (kwargs["z"])
        return o

    def rapid(self, **kwargs):
        self.out("G0 " + self.kwcoord(kwargs))

    def feed(self, **kwargs):
        self.out("F%f G1 %s" % (self.feed_rate, self.kwcoord(kwargs)))

    def zfeed(self, z):
        self.out("F%f G1 Z%f" % (self.plunge_rate, z))

    def line(self, x1, y1, x2, y2):
        self.safez()
        self.rapid(x=x1, y=y1)
        self.zfeed(self.finish_depth)
        self.feed(x=x2, y=y2)
        self.safez()
        
    def arc(self, x1, y1, x2, y2, radius, cw=True):
        self.safez()
        self.rapid(x=x1, y=y1)
        self.zfeed(self.finish_depth)
        self.out("F%f G91.1 G17 %s X%f Y%f R%f" % (self.feed_rate, "G02" if cw else "G03",
                                                    x2, y2, radius))
        self.safez()
        
    def out(self, s):
        self.code.append(s)

    def write(self):
        print "%"
#        print "(Tool Diameter %f)" % (self.tool_diameter)
#        print "(Thickness %f)" % (self.thickness)
#        print "(Delta Z %f" % (self.delta_z)
        print "M6 T1"  # Tool change
        print "S2000"  # (Spindle RPM)
        print "M3"  # (Clockwise spindle on)
        print "G64"  # (Blend without tolerance)"
        for o in self.code:
            print o
        print "%"

    def rectangle(self, center_x, center_y, width, height):
        self.safez()
        roughadj = self.tool_radius + self.finish_cut
        for r in range(1, self.repeat+1):
            self.rapid(x=center_x - width/2 + roughadj, y=center_y - height/2 + roughadj)
            self.zfeed(r*self.delta_z)
            self.feed(x=center_x + width/2 - roughadj)
            self.feed(y=center_y + height/2 - roughadj)
            self.feed(x=center_x - width/2 + roughadj)
            self.feed(y=center_y - height/2 + roughadj)
        if not self.dryrun:
            finish = self.tool_radius
            self.zfeed(self.finish_depth)
            self.feed(x=center_x - width/2 + finish, y=center_y - height/2 + finish)
            self.feed(x=center_x + width/2 - finish)
            self.feed(y=center_y + height/2 - finish)
            self.feed(x=center_x - width/2 + finish)
            self.feed(y=center_y - height/2 + finish)
            self.feed(x=center_x - width/2 + roughadj, y=center_y - height/2 + roughadj)
        self.safez()


class FontPlotter():
    def __init__(self, cxf_file):
        self.char = {}
        self.var = {}
        self.parse(open(cxf_file, "r"))

    def parse(self, fh):
        char = None
        linesleft = 0
        for line in fh:
            var = re.match("^# (\S+):\s+(.*)", line)
            charstart = re.match("^\[(.*)\] (\d+)", line)
            if var:
                self.var[var.group(1)] = var.group(2)
            elif charstart:
                if linesleft != 0:
                    raise Exception("Incomplete character %s / %s" % (line, fh))
                char = charstart.group(1)
                linesleft = int(charstart.group(2))
                self.char[char] = []
            elif linesleft > 0:
                cmd, coords = line.split()
                if cmd not in ["L", "A", "AR"]:
                    raise Exception("Unrecognized command at %s / %s" % (cmd, fh))
                self.char[char].append((cmd, map(lambda s: float(s),
                                                 coords.split(","))))
                linesleft -= 1
        if linesleft != 0:
            raise Exception("Incomplete character at EOF")

    def plotString(self, xc, yc, height, text):
        pass

    def _bounding_box(self, char):
        minx = float("inf")
        miny = float("inf")
        maxx = float("-inf")
        maxy = float("-inf")
        for l in self.char[char]:
            cmd, coords = l[0], l[1]
            if cmd == 'L':
                x1, y1, x2, y2 = coords
                minx = min(x1, x2, minx)
                miny = min(y1, y2, miny)
                maxx = max(x1, x2, maxx)
                maxy = max(y1, y2, maxy)
            elif cmd in ['A', 'AR']:
                # fixme: handle AR
                xcenter, ycenter, radius, start_angle, end_angle = coords
                # find minimum and maximum x, y along arc
                xco = [cos(start_angle * pi/180) * radius + xcenter,
                       cos(end_angle * pi/180) * radius + xcenter]
                yco = [sin(start_angle * pi/180) * radius + ycenter,
                       sin(end_angle * pi/180) * radius + ycenter]
                an = [start_angle]
                if end_angle == 0:
                    end_angle = 360.0

                def axis_intersections():
                    while an[0] < end_angle:
                        an[0] += 90
                        yield int(an[0]/90)*90
                for a in axis_intersections():
                    xco.append(cos(a * pi/180) * radius + xcenter)
                    yco.append(sin(a * pi/180) * radius + ycenter)
                minx = min(minx, min(xco))
                miny = min(miny, min(yco))
                maxx = max(maxx, max(xco))
                maxy = max(maxy, max(yco))

                #print "(char %s: xy %f,%f sa %f ea %f r %f min %f,%f max %f,%f xco %s yco %s" % (
                    #char, xcenter, ycenter, start_angle, end_angle, radius, minx, miny, maxx, maxy, xco, yco)

        print "(bbox %s: %f, %f, %f, %f)" % (char, minx, miny, maxx, maxy)
        return (minx, miny, maxx, maxy)

    # fixme: dont' need to do translation here and in gcode
    def _scale_char(self, height, char):
        # return bounding box + array of lines and arcs
        bx1, by1, bx2, by2 = self._bounding_box(char)
        #bheight = abs(by1-by2)
        #bwidth = abs(bx1-bx2)
        bheight = by2
        bwidth = bx2
        scale = height/bheight

        # this doesn't actually translate
        def scale_and_translate(point):
            return (point[0] * scale,
                    point[1] * scale)

        oa = []
        for l in self.char[char]:
            op = l[0]
            d = l[1]
            o = [op]
            if op == 'L':
                ncoord = len(d) & ~1
                points = [[d[i], d[i+1]] for i in range(0, ncoord, 2)]
                o.extend(map(scale_and_translate, points))
            elif op in ['A', 'AR']:
                # scale and translate xcenter, ycenter
                o.extend(scale_and_translate(d[0:2]))
                # scale radius
                o.append(d[2] * scale)
                # leave start and end angle alone
                o.extend(d[3:])
            oa.append(o)

        #oa.append(['L', scale_and_translate([bx1, by1]), scale_and_translate([bx1, by2])])
        #oa.append(['L', scale_and_translate([bx1, by2]), scale_and_translate([bx2, by2])])
        #oa.append(['L', scale_and_translate([bx2, by2]), scale_and_translate([bx2, by1])])
        #oa.append(['L', scale_and_translate([bx2, by1]), scale_and_translate([bx1, by1])])
        return oa, bwidth*scale, scale

    def _char_to_gcode(self, chardata, x, y, gcw):
        for l in chardata:
            op = l[0]
            if op == 'L':
                p1, p2 = l[1], l[2]
                gcw.line(x + p1[0], y + p1[1], x + p2[0], y + p2[1])
            elif op in ['A', 'AR']:
                xcenter = l[1]
                ycenter = l[2]
                radius = l[3]
                start_angle = l[4]
                end_angle = l[5]
                xstart = cos(start_angle * pi/180) * radius + xcenter + x
                ystart = sin(start_angle * pi/180) * radius + ycenter + y
                xend = cos(end_angle * pi/180) * radius + xcenter + x
                yend = sin(end_angle * pi/180) * radius + ycenter + y
                cw = op == 'AR'  # AR is CW
                gcw.arc(xstart, ystart, xend, yend, radius, cw)

    def plot_text(self, text, centerx, starty, height, gcw):
        scale = None
        totwidth = 0
        for c in text:
            if c == " ":
                totwidth += float(self.var["WordSpacing"])*scale
            else:
                _, width, scale = self._scale_char(height, c)
                width += float(self.var["LetterSpacing"])*scale
            totwidth += width
        # don't include space for last character
        totwidth -= float(self.var["LetterSpacing"])*scale
        x = centerx - totwidth / 2
        for c in text:
            if c == " ":
                x += float(self.var["WordSpacing"])*scale
            else:
                cdata, width, scale = self._scale_char(height, c)
                self._char_to_gcode(cdata, x, starty, gcw)
                x += width
                x += float(self.var["LetterSpacing"])*scale


g = GCodeWriter()
f = FontPlotter("../fonts/normal.cxf")
f2 = FontPlotter("../fonts/cursive.cxf")

def panel_upper_right_holes():
    # 0,0 is upper right of panel

    # rack mounting holes
    g.oval(-0.250, -0.250,  -0.375, -0.250, 0.125)
    g.oval(-0.250, -0.875,  -0.375, -0.875, 0.125)

    # power indicator
    g.circle(-1.75, -0.825, mm(10)/2)
    # fault indicator
    g.circle(-1.75, -2.075, mm(10)/2)
    # stepper power switch
    g.circle(-2.75, -1.450, 0.480/2)   # was .470 and tight

    # vertical LED array
    for i in range(0,4):
        g.circle(-3.625, -0.7 - i*0.5, mm(8)/2)
        g.circle(-4.125, -0.7 - i*0.5, mm(8)/2)

    # horizontal LED array, stepper side
    # center to center width is 1.5"
    for i in range(0,4):
        g.circle(-4.875 - i*0.5, -2.2, mm(8)/2)

    # cutout for voltmeter - top is Y=-0.7 + mm(10)/2 to align with top of LED bezel
    # to center to LEDs, overhang .29/2 each side
    vm_ur_x = -4.875 + .290/2
    vm_ur_y = -0.7 + mm(10)/2
    vm_width = 1.79
    vm_height = 1.03
    g.rectangle(vm_ur_x - vm_width/2, vm_ur_y - vm_height/2, vm_width, vm_height)

    # horizontal LED array, spindle side
    for i in range(0,4):
        g.circle(-4.875 - vm_width - .250 - i*0.5, -2.2, mm(8)/2)

    # Second voltmeter
    vm_ur_x = -4.875 + .290/2 - vm_width - 0.250
    g.rectangle(vm_ur_x - vm_width/2, vm_ur_y - vm_height/2, vm_width, vm_height)

def panel_upper_right_text():
    f.plot_text("POWER", -1.75, -0.825-0.7, 0.2, g)
    f.plot_text("FAULT", -1.75, -2.075-0.7, 0.2, g)

    f.plot_text("ON", -2.75, -1.450+0.7, 0.2, g)
    f.plot_text("OFF", -2.75, -1.450-0.7-0.2, 0.2, g)

    boxleft = -6.645
    boxright = -1.605 + 0.25
    boxtop = -0.25
    boxbot = -2.7
    arcrad = 0.25
    
    g.line(-1.605, -0.25, -2.9, -0.25)
    f2.plot_text("AXIS DRIVE", -4, -0.4, 0.3, g)
    g.line(-5.35, -0.25, -6.645 + .25, -0.25)
    g.arc(boxleft + arcrad, boxtop, boxleft, boxtop - arcrad, arcrad, False)
    g.line(-6.645, -0.5, -6.645, -2.8)
#    g.arc(boxleft, boxbot, boxleft + arcrad, -2.8 - .25, .25, False)

    f2.plot_text("KDAY 2/2015", -4, -3.5, 0.2, g)

    
    f.plot_text("S", -4.125, 4*-0.5 + -0.7, 0.15, g)
    f.plot_text("D", -3.625, 4*-0.5 + -0.7, 0.15, g)

    f.plot_text("X", -4.125 - .35, 0*-0.5 + -0.8, 0.15, g)
    f.plot_text("Y", -4.125 - .35, 1*-0.5 + -0.8, 0.15, g)
    f.plot_text("Z", -4.125 - .35, 2*-0.5 + -0.8, 0.15, g)
    f.plot_text("A", -4.125 - .35, 3*-0.5 + -0.8, 0.15, g)

    f.plot_text("STEPPERS", (-4.875 + .290 / 2) - 1.79/2, -1.9, 0.2, g)

    
    f.plot_text("CP",  -4.875 - 0*0.5, -2.7, 0.15, g)
    f.plot_text("ES", -4.875 - 1*0.5, -2.7, 0.15, g)
    f.plot_text("12v", -4.875 - 2*0.5, -2.7, 0.15, g)
    f.plot_text("5v",  -4.875 - 3*0.5, -2.7, 0.15, g)

    f.plot_text("SPINDLE", (-4.875 + .290 / 2) - 1.79 - 0.250 - 1.79/2, -1.9, 0.2, g)

    
    f.plot_text("MAN",  -4.875 - 1.79 - 0.250 - 0*0.5, -2.7, 0.15, g)
    f.plot_text("EN",  -4.875 - 1.79 - 0.250 - 1*0.5, -2.7, 0.15, g)
    f.plot_text("CW",  -4.875 - 1.79 - 0.250 - 2*0.5, -2.7, 0.15, g)
    f.plot_text("PWM",  -4.875 - 1.79 - 0.250 - 3*0.5, -2.7, 0.15, g)



def panel_upper_left_holes():
    tach_ur_x = -8.81
    tach_width = 2.70
    tach_ur_y = -0.7 + mm(10)/2
    tach_height = 1.33
    g.rectangle(tach_ur_x - tach_width/2, tach_ur_y - tach_height/2, tach_width, tach_height)

def panel_upper_left_text():
    g.line(-8.81 - 2.70/2, 0, -8.81 - 2.70/2, -3)
    f.plot_text("TOOL RPM", -8.81 - 2.70/2, -2.2 - 0.15, 0.3, g)


def engrave(g):
# far too deep
#    g.finish_depth = -0.02
# this is what I used in the test; still mostly too deep
#    g.finish_depth = -0.005
    g.finish_depth = -0.0025  # we'll try this on a flat setup
    g.tool_diameter = 0
    g.tool_radius = 0
    g.safe_z = 0.05


#panel_upper_right_holes()
engrave(g)
panel_upper_right_text()

#panel_upper_left_holes()
#panel_upper_left_text()

g.write()

