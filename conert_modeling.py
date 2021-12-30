import sys, os
from cromosim import *
from cromosim.micro import *
from optparse import OptionParser
import json

plt.ion()


parser = OptionParser(usage="usage: %prog [options] filename",
    version="%prog 1.0")
parser.add_option('--json',dest="jsonfilename",default="input.json",
    type="string",
                  action="store",help="Input json filename")
opt, remainder = parser.parse_args()

with open(opt.jsonfilename) as json_file:
    try:
        input = json.load(json_file)
    except json.JSONDecodeError as msg:
        print(msg)
        print("Failed to load json file ",opt.jsonfilename)
        print("Check its content \
            (https://fr.wikipedia.org/wiki/JavaScript_Object_Notation)")
        sys.exit()


prefix = input["prefix"]
if not os.path.exists(prefix):
    os.makedirs(prefix)
seed = input["seed"]
with_graphes = input["with_graphes"]
json_domains = input["domains"]

json_people_init = input["people_init"]

json_sensors = input["sensors"]

Tf = input["Tf"]
dt = input["dt"]
drawper = input["drawper"]
mass = input["mass"]
tau = input["tau"]
F = input["F"]
kappa = input["kappa"]
delta = input["delta"]
Fwall = input["Fwall"]
lambda_ = input["lambda"]
eta = input["eta"]
projection_method = input["projection_method"]
dmax = input["dmax"]
dmin_people = input["dmin_people"]
dmin_walls = input["dmin_walls"]
plot_p = input["plot_people"]
plot_c = input["plot_contacts"]
plot_v = input["plot_velocities"]
plot_vd = input["plot_desired_velocities"]
plot_pa = input["plot_paths"]
plot_s = input["plot_sensors"]
plot_pa = input["plot_paths"]


domains = {}
for i,jdom in enumerate(json_domains):
    jname = jdom["name"]

    jbg = jdom["background"]
    jpx = jdom["px"]
    jwidth = jdom["width"]
    jheight = jdom["height"]
    jwall_colors = jdom["wall_colors"]
    if (jbg==""):
        dom = Domain(name=jname, pixel_size=jpx, width=jwidth,
                     height=jheight, wall_colors=jwall_colors)
    else:
        dom = Domain(name=jname, background=jbg, pixel_size=jpx,
                     wall_colors=jwall_colors)

    for sl in jdom["shape_lines"]:
        line = Line2D(sl["xx"],sl["yy"],linewidth=sl["linewidth"])
        dom.add_shape(line,outline_color=sl["outline_color"],
                      fill_color=sl["fill_color"])

    for sc in jdom["shape_circles"]:
        circle = Circle( (sc["center_x"], sc["center_y"]), sc["radius"] )
        dom.add_shape(circle,outline_color=sc["outline_color"],
                      fill_color=sc["fill_color"])

    for se in jdom["shape_ellipses"]:
        ellipse = Ellipse( (se["center_x"], se["center_y"]),
                            se["width"], se["height"],
                            se["angle_in_degrees_anti-clockwise"])
        dom.add_shape(ellipse,outline_color=se["outline_color"],
                      fill_color=se["fill_color"])

    for sr in jdom["shape_rectangles"]:
        rectangle = Rectangle( (sr["bottom_left_x"],sr["bottom_left_y"]),
                               sr["width"], sr["height"],
                               sr["angle_in_degrees_anti-clockwise"])
        dom.add_shape(rectangle,outline_color=sr["outline_color"],
                      fill_color=sr["fill_color"])

    for spo in jdom["shape_polygons"]:
        polygon = Polygon(spo["xy"])
        dom.add_shape(polygon,outline_color=spo["outline_color"],
                      fill_color=spo["fill_color"])

    dom.build_domain()

    for j,dd in enumerate(jdom["destinations"]):
        desired_velocity_from_color=[]
        for gg in dd["desired_velocity_from_color"]:
            desired_velocity_from_color.append(
                np.concatenate((gg["color"],gg["desired_velocity"])))
        dest = Destination(name=dd["name"],colors=dd["colors"],
        excluded_colors=dd["excluded_colors"],
        desired_velocity_from_color=desired_velocity_from_color,
        velocity_scale=dd["velocity_scale"],
        next_destination=dd["next_destination"],
        next_domain=dd["next_domain"],
        next_transit_box=dd["next_transit_box"])

        dom.add_destination(dest)
        
        if (with_graphes):
            dom.plot_desired_velocity(dd["name"],id=100*i+10+j,step=20)


    if (with_graphes):
        dom.plot_wall_dist(id=100*i+1,step=20)

    domains[dom.name] = dom


all_sensors = {}
for domain_name in domains:
    all_sensors[domain_name] = []
for s in json_sensors:
    s["id"] = []
    s["times"] = []
    s["xy"] = []
    s["dir"] = []
    all_sensors[s["domain"]].append(s)

t = 0.0
counter = 0


all_people = {}
for i,peopledom in enumerate(json_people_init):
    dom = domains[peopledom["domain"]]
    groups = peopledom["groups"]

    people = people_initialization(dom, groups, dt,
        dmin_people=dmin_people, dmin_walls=dmin_walls, seed=seed,
        itermax=10, projection_method=projection_method, verbose=True)
    I, J, Vd = dom.people_desired_velocity(people["xyrv"],
        people["destinations"])
    people["Vd"] = Vd
    for ip,pid in enumerate(people["id"]):
        people["paths"][pid] = people["xyrv"][ip,:2]
    contacts = None
    if (with_graphes):
        colors = people["xyrv"][:,2]
        plot_people(100*i+20, dom, people, contacts, colors, time=t,
                    plot_people=plot_p, plot_contacts=plot_c,
                    plot_velocities=plot_v, plot_desired_velocities=plot_vd,
                    plot_sensors=plot_s, sensors=all_sensors[dom.name],
                    savefig=True, filename=prefix+dom.name+'_fig_'+ \
                    str(counter).zfill(6)+'.png')
    all_people[peopledom["domain"]] = people


cc = 0
draw = True

while (t<Tf):



    for idom,name in enumerate(domains):

        dom = domains[name]
        people = all_people[name]
        I, J, Vd = dom.people_desired_velocity(people["xyrv"],
            people["destinations"])
        people["Vd"] = Vd
        people["I"] = I
        people["J"] = J


    virtual_people = find_duplicate_people(all_people, domains)


    for idom,name in enumerate(domains):

        dom = domains[name]
        people = all_people[name]

        try:
            xyrv = np.concatenate((people["xyrv"],
                virtual_people[name]["xyrv"]))
            Vd = np.concatenate((people["Vd"],
                virtual_people[name]["Vd"]))
            Uold = np.concatenate((people["Uold"],
                virtual_people[name]["Uold"]))
        except:
            xyrv = people["xyrv"]
            Vd = people["Vd"]
            Uold = people["Uold"]

        if (xyrv.shape[0]>0):

            if (np.unique(xyrv, axis=0).shape[0] != xyrv.shape[0]):
                sys.exit()

            contacts = compute_contacts(dom, xyrv, dmax)
            Forces = compute_forces( F, Fwall, xyrv, contacts, Uold, Vd,
                                     lambda_, delta, kappa, eta)
            nn = people["xyrv"].shape[0]
            all_people[name]["U"] = dt*(Vd[:nn,:]-Uold[:nn,:])/tau + \
                          Uold[:nn,:] + \
                          dt*Forces[:nn,:]/mass
            virtual_people[name]["U"] = dt*(Vd[nn:,:]-Uold[nn:,:])/tau + \
                          Uold[nn:,:] + \
                          dt*Forces[nn:,:]/mass


            all_people[name], all_sensors[name] = move_people(t, dt,
                                           all_people[name],
                                           all_sensors[name])

        if (draw and with_graphes):
            colors =  all_people[name]["xyrv"][:,2]
            plot_people(100*idom+20, dom, all_people[name], contacts,
                        colors, virtual_people=virtual_people[name], time=t,
                        plot_people=plot_p, plot_contacts=plot_c,
                        plot_paths=plot_pa, plot_velocities=plot_v,
                        plot_desired_velocities=plot_vd, plot_sensors=plot_s,
                        sensors=all_sensors[dom.name], savefig=True,
                        filename=prefix+dom.name+'_fig_'
                        + str(counter).zfill(6)+'.png')
            plt.pause(0.01)


    all_people = people_update_destination(all_people,domains,dom.pixel_size)


    for idom,name in enumerate(domains):
        all_people[name]["Uold"] = all_people[name]["U"]



    t += dt
    cc += 1
    counter += 1
    if (cc>=drawper):
        draw = True
        cc = 0
    else:
        draw = False


for idom,domain_name in enumerate(all_sensors):
    plot_sensors(100*idom+40, all_sensors[domain_name], t, savefig=True,
                filename=prefix+'sensor_'+str(i)+'_'+str(counter)+'.png')
    plt.pause(0.01)

plt.ioff()
plt.show()
sys.exit()