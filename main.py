#!/usr/bin/env python3
import json
from konverter import coords_relative, positions, coords_global
import matplotlib.pyplot as plt
from math import sin, cos, radians, degrees
import numpy as np
import os
import argparse
from matplotlib.patches import Ellipse, Polygon

# Disable trajectory curving
USE_CURVING = False
data_json = []
s_lat, s_lon = 0, 0
loaded_traj = False


def plot_data(datas, filename, show, s_lat, s_lon, ax=None, start_coords=None, p_time=0, radius=2, text=True,
              show_dist=True, show_coords=True):
    """
    This function plots all items in data with velocity plot and
    :param show_coords: Show coords in WGS84
    :param s_lat: start latitude
    :param s_lon: start longitude
    :param show_dist: show critical distances
    :param text: flag to plot text
    :param radius: Safe radius
    :param p_time: Current time moment in percents of amount time
    :param start_coords: start coords for relative coords
    :param show: show all plots in figure window
    :param ax: axes to plot
    :param datas: JSON with path
    :param filename: name of file, used to save image
    :return: void
    """
    if ax is None:
        fig, ax = plt.subplots()
    if not start_coords:
        # End coordinates of previous segment,
        # used for curving
        pX, pY = 0, 0
    else:
        pX, pY = start_coords[0], start_coords[1]
    # By default, start_time is null
    current_coords = []
    velocities = []
    for data in datas:
        if isinstance(data, list):
            break
        start_time = 0
        time = p_time * data['time']
        for item in data['items']:
            Rarc, X, Xc, Y, Yc, dx, dy, pX, pY, vel = plot_items(ax, data, datas, item, pX, pY)
            # Plotting current targets pose
            # Plot half-hour ticks
            for tick in range(20):
                dtime = tick * 1800
                plot_position(Xc, Yc, ax, current_coords, data, datas, dx, dy, item, pX, pY, radius, s_lat, s_lon,
                              show_coords, start_time, text, dtime, ticks=True)
            plot_position(Xc, Yc, ax, current_coords, data, datas, dx, dy, item, pX, pY, radius, s_lat, s_lon,
                          show_coords, start_time, text, time, ticks=False)
            # Adding previous point
            if item['curve'] == 0:
                pX, pY = pX + X, -(pY + Y)
            else:
                pX, pY = X[-1], Y[-1]
            start_time += item['duration']
            if not datas.index(data):
                velocities.append(vel)
    # Check distance and plot it
    our = current_coords[0]
    for coords in current_coords:
        dist = ((our[0] - coords[0]) ** 2 + (our[1] - coords[1]) ** 2) ** 0.5
        if coords != our:
            if 2 * radius < dist < 3 * radius:
                ax.plot([our[0], coords[0]], [our[1], coords[1]], linewidth=1.5, color='y')
                if show_dist:
                    ax.text(0.5 * (our[0] + coords[0]), 0.5 * (our[1] + coords[1]), str(round(dist, 2)))
            elif dist < 2 * radius:
                ax.plot([our[0], coords[0]], [our[1], coords[1]], linewidth=2, color='darkred')
                if show_dist:
                    ax.text(0.5 * (our[0] + coords[0]), 0.5 * (our[1] + coords[1]), str(round(dist, 2)),
                            fontdict={'color': 'darkred', 'weight': 'bold'})
    ax.set(xlabel='Time: ' + str(round(time / 3600, 2)) + ' h', ylabel='y',
           title='Trajectory')
    ax.grid()
    if show:
        plt.show()
    return velocities


def plot_position(Xc, Yc, ax, current_coords, data, datas, dx, dy, item, pX, pY, radius, s_lat, s_lon,
                  show_coords, start_time, text, time, ticks=False):
    """
    This method plot current positions or half-hour ticks
    It also displays info about speed and cords
    :param Xc: center x
    :param Yc: center y
    :param ax: axes of plot
    :param current_coords: current coordinates
    :param data: array with items
    :param datas: dict with ships
    :param dx: offset x
    :param dy: offset y
    :param item: current item
    :param pX: previous x
    :param pY: previous y
    :param radius: danger radius
    :param s_lat: start latitude
    :param s_lon: start longitude
    :param show_coords: flag to show global coords
    :param start_time: time of beginning curve
    :param text: flag to show text
    :param time: current time
    :param ticks: flag to show half-hour ticks
    :return:
    """
    plt.rcParams.update({'font.size': 7})
    vel = item['length'] / item['duration']
    if time - start_time < item['duration'] and time >= start_time:
        if item['curve'] == 0:
            Xt, Yt = positions(item['begin_angle'], vel * (time - start_time))
            if not ticks:
                if datas.index(data) == 0:
                    ax.plot(pY + Yt, pX + Xt, marker='D', color='b')
                    # Draw "save circle"
                    danger_r = plt.Circle((pY + Yt, pX + Xt), radius, color='b', fill=False)
                else:
                    ax.plot(pY + Yt, pX + Xt, marker='D', color='r')
                    # Draw "save circle"
                    danger_r = plt.Circle((pY + Yt, pX + Xt), radius, color='r', fill=False)
                ax.add_artist(danger_r)
                current_coords.append([pY + Yt, pX + Xt])
                if show_coords:
                    clat, clon = coords_global(pX + Xt, pY + Yt, s_lat, s_lon)
                    if s_lat == 0 and s_lon == 0:
                        cord_str = str(round(pX + Xt, 2)) + ' nm ' + '\n' + \
                                   str(round(pY + Yt, 2)) + ' nm'
                    else:
                        cord_str = str(clat) + '° ' + '\n' + str(clon) + '°'
                else:
                    cord_str = ''
                if text:
                    if datas.index(data) != 0:
                        ax.text(pY + Yt - 0.5, pX + Xt + 0.5, 'Tar ' + str(datas.index(data)) + '\n'
                                + str(round(vel * 3600, 1)) + ' knt' + '\n' + cord_str)
                    else:
                        ax.text(pY + Yt, pX + Xt, str(round(vel * 3600, 1)) + ' knt' + '\n' + cord_str)
            else:
                ax.plot(pY + Yt, pX + Xt, marker='o', color='yellow', markersize=1)
        else:
            # False angular sign velocity direction
            Rarc = 1 / item['curve']
            ang_vel = -vel * item['curve']
            Xt = Rarc * cos(radians(90 - item['begin_angle']) +
                            ang_vel * (time - start_time)) + Xc - dx
            Yt = -(Rarc * sin(radians(90 - item['begin_angle']) +
                              ang_vel * (time - start_time)) + Yc - dy)
            if not ticks:
                if datas.index(data) == 0:
                    ax.plot(Yt, Xt, marker='D', color='b')
                    # Draw "save circle"
                    danger_r = plt.Circle((Yt, Xt), radius, color='b', fill=False)
                else:
                    ax.plot(Yt, Xt, marker='D', color='r')
                    # Draw "save circle"
                    danger_r = plt.Circle((Yt, Xt), radius, color='r', fill=False)
                ax.add_artist(danger_r)
                current_coords.append([Yt, Xt])
                if show_coords:
                    clat, clon = coords_global(Xt, Yt, s_lat, s_lon)
                    if s_lat == 0 and s_lon == 0:
                        cord_str = str(round(Xt, 2)) + ' nm ' + '\n' + str(round(Yt, 2)) + ' nm'
                    else:
                        cord_str = str(clat) + '° ' + '\n' + str(clon) + '°'
                else:
                    cord_str = ''
                if text:
                    if datas.index(data) != 0:
                        ax.text(Yt - 0.5, Xt + 0.5, 'Tar ' + str(datas.index(data)) + '\n'
                                + str(round(vel * 3600, 1)) + ' knt' + '\n' + cord_str)
                    else:
                        ax.text(Yt, Xt, str(round(vel * 3600, 1)) + ' knt' + '\n' + cord_str)
            else:
                ax.plot(Yt, Xt, marker='o', color='yellow', markersize=1)


def plot_items(ax, data, datas, item, pX, pY):
    """
    Plot trajectory items
    :param ax: graphics
    :param data: current ship
    :param datas: all ships
    :param item: current item
    :param pX: previous x
    :param pY: previous y
    :return: Curve radius, trajectory params, velocity
    """
    vel = item['length'] / item['duration']
    if not USE_CURVING:
        pX, pY = item['X'], item['Y']
    if item['curve'] == 0:
        # For lines
        X, Y = positions(item['begin_angle'], item['length'])
        if datas.index(data) != 0:
            ax.plot([pY, pY + Y], [pX, pX + X], linewidth=2, color='brown')
        else:
            ax.plot([pY, pY + Y], [pX, pX + X], linewidth=2)
        Rarc = 0
        Xc, Yc, dx, dy = 0, 0, 0, 0
    else:
        # For arcs
        if item['curve'] > 0:
            Xc, Yc = positions(item['begin_angle'] + 90,
                               1 / item['curve'])
        else:
            Xc, Yc = positions(item['begin_angle'] - 90,
                               1 / item['curve'])
        angle = item['begin_angle']
        Rarc = 1 / item['curve']
        dx = (Rarc * cos(radians(90 - angle)) + Xc - pX)
        if not USE_CURVING:
            dy = (Rarc * sin(radians(90 - angle)) + Yc + pY)
        else:
            # Some hotfix
            dy = (Rarc * sin(radians(90 - angle)) + Yc - pY)
        dangle = degrees(item['length'] * item['curve'])
        X = []
        Y = []
        for angle in np.arange(item['begin_angle'], item['begin_angle'] + dangle, dangle / 100):
            X.append(Rarc * cos(radians(90 - angle)) + Xc - dx)
            Y.append(-(Rarc * sin(radians(90 - angle)) + Yc - dy))
        if datas.index(data) != 0:
            ax.plot(Y, X, linewidth=2, color='brown')
        else:
            ax.plot(Y, X, linewidth=2)
    return Rarc, X, Xc, Y, Yc, dx, dy, pX, pY, vel


def prepare_file(filename, show, ax=None, rel=False, tper=0, radius=2, text=True, show_dist=True,
                 show_coords=True, figure=None, is_loaded=False):
    """
    Prepares route JSON for plotting,
    changes geodesic coords to relative
    :param show_coords: Show coords in WGS84
    :param is_loaded: Flag to update JSON file
    :param figure: matplotlib figure to plot velocities
    :type figure: matplotlib figure
    :param show_dist: show dist values
    :param text: Show velocities text
    :param radius: danger radius for ships
    :param tper: percent of amount time
    :param rel: use relative coords in JSON
    :param ax: axis to plot
    :type ax: matplotlib axes
    :param filename: JSON route filename
    :return: dictionary with translated route
    """
    ax.set_facecolor((159 / 255, 212 / 255, 251 / 255))
    try:
        if is_loaded:
            key1, key2 = 'X', 'Y'
        data_all = []
        global data_json, s_lat, s_lon
        if check_type(filename) == 'poly':
            plot_limits(ax, filename)
            return
        if not is_loaded:
            with open(filename) as f:
                datas = json.loads(f.read())
                # Start coordinates
                try:
                    key1, key2 = 'x', 'y'
                    rel = True
                    s_lat, s_lon = datas[0]['items'][0][key1], datas[0]['items'][0][key2]
                except KeyError:
                    rel = False
                    key1, key2 = 'lat', 'lon'
                    s_lat, s_lon = datas[0]['items'][0][key1], datas[0]['items'][0][key2]
                for data in datas:
                    new_data = {'items': []}
                    time = 0
                    for item in data['items']:
                        obj = {}
                        for key in list(item.keys()):
                            if key != key1 and key != key2:
                                obj[key] = item[key]
                        # Translate coordinates
                        if not rel:
                            obj['X'], obj['Y'] = coords_relative(s_lat, s_lon, item[key1], item[key2])
                        else:
                            # If use relative coords, fields lat and lon should contain X and Y
                            obj['X'], obj['Y'] = item[key1], item[key2]
                        time += item['duration']
                        new_data['items'].append(obj)
                    new_data['time'] = time
                    data_all.append(new_data)
                # new_data['start_time'] = data['start_time']
                data_json = data_all
                data_json.append([s_lat, s_lon])
        else:
            data_all = data_json
            s_lat, s_lon = data_all[len(data_all) - 1][0], data_all[len(data_all) - 1][1]
            # print('not_loaded')
        if rel:
            vel = plot_data(data_all, filename, show, s_lat, s_lon, ax, [s_lat, s_lon], p_time=tper, radius=radius,
                            text=text,
                            show_dist=show_dist, show_coords=show_coords)
        else:
            vel = plot_data(data_all, filename, show, s_lat, s_lon, ax, p_time=tper, radius=radius, text=text,
                            show_dist=show_dist, show_coords=show_coords)

        if figure is not None:
            ax1 = figure.figure.add_subplot(111)
            ax1.clear()

            X = []
            Y = []
            n = 0
            for v in vel:
                X.append(n)
                X.append(n + 1)
                Y.append(v * 3600)
                Y.append(v * 3600)
                n += 1
                # ax1.text((2*n+1)/2, v*3600, str(round(v * 3600, 1)) + ' knt')
            ax1.plot(X, Y, linewidth=3)
            ax1.set(xlabel='N of part', ylabel='Vel, knots',
                    title='Velocity')
            ax1.grid()
            ax1.set_ylim([-1, 25])
            figure.draw()
        return data_all
    except:
        return None


def plot_limits(ax, filename):
    """
    This function plots navigation limits
    :param ax: axes
    :param filename: file with limitations
    :return:
    """
    with open(filename) as f:
        data = json.loads(f.read())
        polygons = [item for item in data['features']
                    if item['geometry']['type'] == 'Polygon']
        points = [item for item in data['features']
                  if item['geometry']['type'] == 'Point']
        lines = [item for item in data['features']
                 if item['geometry']['type'] == 'LineString']
        plot_polygons(ax, polygons)
        plot_points(ax, points)
        plot_lines(ax, lines)


def plot_lines(ax, lines):
    """
    Plot line_crossing_prohibition objects
    :param ax: axes
    :param lines: array with lines
    :return:
    """
    global s_lat, s_lon
    for obj in lines:
        coords = obj['geometry']['coordinates']
        coords_x = [coords_relative(s_lat, s_lon, item[0], item[1])[0] for item in coords]
        coords_y = [coords_relative(s_lat, s_lon, item[0], item[1])[1] for item in coords]
        ax.plot(coords_x, coords_y, marker='D', color='r')


def plot_points(ax, points):
    """
    Plot point_approach_prohibition objects
    :param ax: axes
    :param points: array with points
    :return:
    """
    global s_lat, s_lon
    for obj in points:
        coords = obj['geometry']['coordinates']
        dist = obj['properties']['distance']
        coords = coords_relative(s_lat, s_lon, coords[0], coords[1])
        ax.plot(coords[0], coords[1], marker='*', color='r')
        ax.add_patch(Ellipse([coords[0], coords[1]], dist, dist, fill=False,
                             hatch='/', color='red'))


def plot_polygons(ax, polygons):
    """
    Plot polygons
    :param ax: axes
    :param polygons: array with polygons
    :return:
    """
    global s_lat, s_lon
    for obj in polygons:
        coords = obj['geometry']['coordinates']
        coords = [coords_relative(s_lat, s_lon, item[0], item[1]) for item in coords[0]]
        if obj['properties']['limitation_type'] == "zone_entering_prohibition":
            ax.add_patch(Polygon(coords, closed=True,
                                 fill=False, hatch='/', color='red'))
        elif obj['properties']['limitation_type'] == "movement_parameters_limitation":
            ax.add_patch(Polygon(coords, closed=True,
                                 fill=False, hatch='|', color='orange'))


def check_type(filename):
    """
    This function is used to detect polygonal files
    :param filename: filename
    :return:
    """
    with open(filename) as f:
        datas = json.loads(f.read())
        try:
            # If file with polygons
            if datas['type'] == "FeatureCollection":
                return 'poly'
        except:
            return 'traj'


def make_all(path, show):
    """
    Makes for all files in directory
    :param path: directory with datafiles
    :return: void
    """
    files = os.listdir(path)
    for file in files:
        if file[-4:] == 'json':
            check_type(path + '/' + file, show)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test scenario plotter")
    parser.add_argument("casefile", type=str, help="Name of file or folder, when -a is used")
    parser.add_argument("-a", action="store_true", help="Makes all files")
    parser.add_argument("-s", action="store_true", help="Show image")
    args = parser.parse_args()
    if args.a:
        print("Making for all files in path: ",
              args.casefile)
        make_all(args.casefile, args.s)
    else:
        print("Making for file: ", args.casefile)
        prepare_file(args.casefile, args.s)
