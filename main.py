import datetime as datetime
import os
import re
import sys
from os import listdir
from os.path import isdir, isfile, join
from pathlib import Path

import pymysql
import pandas as pd
import openpyxl

import numpy as np
import argparse

db_root = os.getenv('db_root')
db_name = os.getenv('db_name')
db_passwd = os.getenv('db_passwd')
db_svr = os.getenv('db_server')
db_root = db_root if db_root else "mtr"
db_name = db_name if db_name else "zs_mtr_db3"
db_passwd = db_passwd if db_passwd else "Passwd88!"
db_svr = db_svr if db_svr else '192.168.11.160'

db = pymysql.connect(host=db_svr, db=db_name, user=db_root, password=db_passwd)
db.autocommit(False)
cursor = db.cursor()


class Route_1:
    def __init__(self, m, r):
        if r == '???':
            self.min_lat = 999999
            self.max_lat = 0
        else:
            self.min_lat = m
            self.max_lat = m
        self.route = [r]
        self.loss_95_99 = {}
        self.loss_90_95 = {}

    def append_and_check_loss_lat(self, node, loss, lat):
        self.route.append(node)
        if node != '???':
            self.max_lat = lat if self.max_lat < lat else self.max_lat
            self.min_lat = lat if lat < self.min_lat else self.min_lat
            if 0.95 <= loss < 100.0:
                if node in self.loss_95_99.keys():
                    self.loss_95_99[node] += 1
                else:
                    self.loss_95_99[node] = 1
            if 0.9 <= loss < 95.0:
                if node in self.loss_90_95.keys():
                    self.loss_90_95[node] += 1
                else:
                    self.loss_90_95[node] = 1


class Dest_Routes:
    def __init__(self, host_index, sme, dest):
        self.host_index = host_index
        self.sme = sme
        self.dest = dest
        self.route = None
        self.loss_95_99 = {}
        self.loss_90_95 = {}
        self.min_duration = 999999
        self.max_lat_of_min_duration = 0
        self.min_lat_of_min_duration = 999999
        self.max_duration = 0
        self.max_lat_of_max_duration = 0
        self.min_lat_of_max_duration = 999999

    def exist_key(self, key):
        return key == self.dest

    def update_loss_lat(self, route2):

        delta_2 = route2.max_lat - route2.min_lat
        if delta_2 < self.min_duration:
            self.min_duration = delta_2
            self.max_lat_of_min_duration = route2.max_lat
            self.min_lat_of_min_duration = route2.min_lat
        if self.max_duration < delta_2:
            self.max_duration = delta_2
            self.max_lat_of_max_duration = route2.max_lat
            self.min_lat_of_max_duration = route2.min_lat
        for node in route2.loss_95_99.keys():
            if node in self.loss_95_99:
                self.loss_95_99[node] += route2.loss_95_99[node]
            else:
                self.loss_95_99[node] = route2.loss_95_99[node]
        for node in route2.loss_90_95.keys():
            if node in self.loss_90_95:
                self.loss_90_95[node] += route2.loss_90_95[node]
            else:
                self.loss_90_95[node] = route2.loss_90_95[node]


class MTR:
    def __init__(self, src, start, tz):
        self.src = src
        self.start = start
        self.tz = tz
        self.route = []
        self.ping = []
        self.count = 1

    def add_route(self, node):
        self.route.append(node)

    def add_ping(self, node, lost, snt, last, avg, best, wrst, stdev):
        self.ping.append((node, lost, snt, last, avg, best, wrst, stdev))

    def inc_count(self):
        self.count += 1

    def is_same(self, ns0):
        if self.route == ns0.route_1_temp:
            return 1
        else:
            return 0


def get_latest_id():
    cursor.execute("SELECT LAST_INSERT_ID()")
    r = cursor.fetchone()[0]
    return r


def insert_db(sql, val=None):
    # print(sql)
    if val is None:
        cursor.execute(sql)
    else:
        cursor.execute(sql, val)
    return get_latest_id()


def get_host_dict():
    hlist = get_host_list()
    host_dict = {}
    for h in hlist:
        host_dict[h[0]] = h[1:]
    return host_dict


def get_host_index(hostname, hostname_ip, sme):
    sql = f"SELECT id from host_index where hostname='{hostname}' and hostname_ip='{hostname_ip}' and sme='{sme}'"
    cursor.execute(sql)
    if cursor.rowcount:
        r = cursor.fetchone()[0]
        return r
    else:
        return 0


def get_host_list(sme=''):
    sql = f"select id, hostname, hostname_ip, sme from host_index"
    if sme:
        sql += f" where sme like '%{sme}%'"

    print(sql)
    cursor.execute(sql)
    return cursor.fetchall()


def get_mtr(startdate, enddate, sme='', dest=None):
    delta_10 = [['sme', 'mtr id', 'host', "dest", 'start_date', 'start_time', 'node ip',
                 'delta avg']]
    delta_50 = [['sme', 'mtr id', 'host', "dest", 'start_date', 'start_time', 'node ip',
                 'delta avg']]
    delta_100 = [['sme', 'mtr id', 'host', "dest", 'start_date', 'start_time', 'node ip',
                  'delta avg']]
    delta_10_dict = {}
    delta_50_dict = {}
    delta_100_dict = {}
    hlist = get_host_list(sme)

    host_dict = {}
    for h in hlist:
        host_dict[h[0]] = h[1:]  # id -> hostname, nostname_ip, sme

    hlist_dict_by_name = {}
    for h in hlist:
        hlist_dict_by_name[h[1]] = h[:1] + h[2:]  # hostname -> id, nostname_ip, sme
    print("host_dict")
    print(host_dict.keys())
    print(hlist_dict_by_name.keys())

    mtr_list0 = get_mtr_id_by_daterange(startdate, enddate, sme, dest)
    # print(mtr_list.keys())
    # exit()

    # mtr_list = {}
    # for records in mtr_list0.values():
    #     for row in records:
    #         key = row[1]  # 'tamj-u22-14'
    #         if key not in mtr_list:
    #             mtr_list[key] = ()
    #         # タプルを連結して構造を維持
    #         mtr_list[key] = mtr_list[key] + (row,)
    #         # mtr_list[key].append(row)
    # print(mtr_list)
    temp_result = {}

    # 1. ホスト名をキーにして一度リストにまとめる
    for records in mtr_list0.values():
        for row in records:
            key = row[1]
            if key not in temp_result:
                temp_result[key] = []
            temp_result[key].append(row)

    # 2. ソートしてタプルに変換する
    mtr_list = {}
    for key, rows in temp_result.items():
        # 日付(row[4])と時刻(row[5])で昇順ソート
        sorted_rows = sorted(rows, key=lambda x: (x[4], x[5]))
        # リストをタプルに変換して格納
        print(hlist_dict_by_name[key])
        mtr_list[key] = tuple(sorted_rows)  # + [hlist_dict_by_name[key][2]])
    print(f"mtr_list {sme} {dest} {startdate} {enddate}")
    print(mtr_list)

    sheet = {}
    latMtr = [[]]
    for host_name in sorted(mtr_list.keys()):  # key is host_index.
        # host_index -> mtr list
        print(f"m = {host_name}")
        print(mtr_list[host_name])

        f = [['DEST IP', 'date', '', 'option', 'sme', 'Internal ID']]
        for mtr_list_by_host in mtr_list[host_name]:  # mtr list with host_index=m
            # each mtr
            nl = []
            # print(f"mtr id= {mtr_list_by_host[0]}")
            # print(host_index)
            f += [[mtr_list_by_host[3], mtr_list_by_host[4], mtr_list_by_host[5],
                   mtr_list_by_host[2], host_name, mtr_list_by_host[0]]]
            f += [['Node', 'HOST', 'Loss%', 'Snt', 'Last', 'Avg', 'Best', 'Wrst', 'StDev', 'Delta Avg']]
            print(mtr_list_by_host)
            nodes = get_mtr_nodes_by_mtrid(mtr_list_by_host[0])

            ave0 = 0
            latOnFlag = False
            aveLine = 0
            for n in nodes:
                # print(f"n = {n}")
                nn = list(n)  # each node line

                # delta latency AVG
                if n[1] != '???':
                    # print(n[1])
                    ave1 = n[5]
                    if ave0 > 0:
                        delta = ave1 - ave0
                        nn.append(delta)
                        if delta > 10.0:
                            delta_10 += [[host_name, mtr_list_by_host[0],
                                          mtr_list_by_host[1], mtr_list_by_host[3],
                                          mtr_list_by_host[4], mtr_list_by_host[5],
                                          n[1], delta]]
                            if n[1] in delta_10_dict.keys():
                                delta_10_dict[n[1]] += 1
                            else:
                                delta_10_dict[n[1]] = 1
                        if delta > 50.0:
                            delta_50 += [[host_name, mtr_list_by_host[0],
                                          mtr_list_by_host[1], mtr_list_by_host[3],
                                          mtr_list_by_host[4], mtr_list_by_host[5],
                                          n[1], delta]]
                            if n[1] in delta_50_dict.keys():
                                delta_50_dict[n[1]] += 1
                            else:
                                delta_50_dict[n[1]] = 1
                        if delta > 100.0:
                            delta_100 += [[host_name, mtr_list_by_host[0],
                                           mtr_list_by_host[1], mtr_list_by_host[3],
                                           mtr_list_by_host[4], mtr_list_by_host[5],
                                           n[1], delta]]
                            if n[1] in delta_100_dict.keys():
                                delta_100_dict[n[1]] += 1
                            else:
                                delta_100_dict[n[1]] = 1

                        # check if ave is continuous high
                        if aveLine < 0.1:  # 0
                            aveLine = delta
                        else:
                            if latOnFlag:
                                if delta < -10:
                                    latOnFlag = False
                            else:  # latFlag == False
                                if delta > 50:
                                    latOnFlag = True

                            nn.append(latOnFlag)

                    else:
                        nn.append(0)
                    ave0 = ave1
                else:
                    nn.append(0)
                # print(f"nn = {nn}")
                f += [nn]
            # print(f"f = {f} ")
            # end of for n in nodes
            if latOnFlag:
                latMtr += [[mtr_list_by_host[3], mtr_list_by_host[4],
                            mtr_list_by_host[5],
                            mtr_list_by_host[2], hlist_dict_by_name[host_name],
                            mtr_list_by_host[0]]]
            f += [[]]
        print(f"{mtr_list[host_name][0][1]}:{hlist_dict_by_name[host_name][2]}")
        # print(f"f = {f}")
        sheet[f"{mtr_list[host_name][0][1]}:{hlist_dict_by_name[host_name][2]}"] = f

    sheet['1.high:latency'] = latMtr

    f = [['node more than 100ms delta', startdate, enddate]]
    f += [['node ip', 'count']]
    for k in sorted(delta_100_dict.keys()):
        f += [[k, delta_100_dict[k]]]
    f += [[]]
    f += [['list of node more than 100ms delta']]
    f += delta_100
    sheet['0.delta_100:all'] = f

    f = [['node more than 50ms delta', startdate, enddate]]
    f += [['node ip', 'count']]
    for k in sorted(delta_50_dict.keys()):
        f += [[k, delta_50_dict[k]]]
    f += [[]]
    f += [['list of node more than 50ms delta']]
    f += delta_50
    sheet['0.delta_50:all'] = f

    f = [['node more than 10ms delta']]
    f += [['node ip', 'count']]
    for k in sorted(delta_10_dict.keys()):
        f += [[k, delta_10_dict[k]]]
    f += [[]]
    f += [['list of node more than 10ms delta', startdate, enddate]]
    f += delta_10
    sheet['0.delta_10:all'] = f
    return sheet


#

def get_mtr_id(dir, name, host_index):
    sql = (f"SELECT id from mtr "
           f"where dir='{dir}' and name='{name}' and host_index='{host_index}'")
    cursor.execute(sql)
    if cursor.rowcount:
        r = cursor.fetchone()[0]
        return r
    else:
        return 0


def get_mtr_id_by_daterange(startdate, enddate, sme, dest):
    sql = f"select host_index from mtr "
    if sme:
        sql += f"join host_index on host_index.id = host_index "
    sql += f" where dateid between {startdate} and {enddate} "
    if sme:
        sql += f"and host_index.sme like '%{sme}%' "
    if dest:
        for i, d in enumerate(dest):
            if i == 0:
                sql += f"and ( dest='{d}' "
            else:
                sql += f"or dest='{d}' "
        sql += ") "
    sql += f"group by host_index order by dateid"
    print(sql)
    cursor.execute(sql)
    hostlist = cursor.fetchall()
    print(hostlist)
    mtr_list = {}
    for h in hostlist:
        print(h[0])
        # select id, host, mtr_option, dest, start_date, start_time from mtr where dateid between {startdate} and {enddate} and host_index={h[0]} order by dateid
        sql = f"select mtr.id, host, mtr_option, dest, start_date, start_time from mtr "
        # if sme:
        #     sql += f"join host_index on host_index.sme like '%{sme}%' "
        sql += f"where dateid between {startdate} and {enddate} and host_index={h[0]} "
        if dest:
            for i, d in enumerate(dest):
                if i == 0:
                    sql += f"and ( dest='{d}' "
                else:
                    sql += f"or dest='{d}' "
            sql += ") "

        sql += "order by dateid "
        # print(sql)
        cursor.execute(sql)
        mtr_list[h[0]] = cursor.fetchall()
        # print(mtr_list[h[0]] )
    return mtr_list


def get_mtr_nodes_by_mtrid(mtrid):
    sql = f"select idx,node,loss,snt,last,ave,best,wrst,stdev from mtr_node where mtr_index={mtrid} order by idx"
    # SELECT      n.idx,     CONCAT_WS(', ', n.node, ip.node) AS nodes,     n.loss,     n.snt,     n.last,     n.ave,     n.best,     n.wrst,     n.stdev FROM      mtr_node n LEFT JOIN      mtr_node_ip ip ON n.id = ip.mtr_node_id WHERE      n.id = 143897549;
    sql = (
        f"SELECT n.idx, CONCAT_WS(' ', n.node, ip.node) AS nodes, "
        f"n.loss, n.snt, n.last, n.ave, n.best, n.wrst, n.stdev FROM mtr_node n "
        f"LEFT JOIN  mtr_node_ip ip ON n.id = ip.mtr_node_id WHERE n.mtr_index = {mtrid} order by idx;")
    cursor.execute(sql)
    return cursor.fetchall()


def get_node_lost(host_index, startdate, enddate, l1, l2):
    sql = (f"select node,count(node) from mtr_node "
           f"join mtr on mtr.id = mtr_node.mtr_index "
           f"where (mtr.dateid between {startdate} and {enddate}) and "
           f"mtr.host_index={host_index} and "
           f"(mtr_node.loss between {l1} and {l2}) group by node")
    cursor.execute(sql)
    return cursor.fetchall()


def insert_or_get_host_index(hostname, hostname_ip, sme, ipzscaler):
    hid = get_host_index(hostname, hostname_ip, sme)
    if hid == 0:
        sql = f"insert into host_index(hostname, hostname_ip, sme, ipzscaler) values(%s, %s, %s, %s)"
        val = (hostname, hostname_ip, sme, ' '.join(ipzscaler))
        print(sql)
        print(val)
        hid = insert_db(sql, val)

        # insert_db(f"insert cloud_index(name) values('{name}')")
    return hid


def insert_mtr_node(mid, idx, node, loss, snt, last, ave, best, wrst, stdev):
    sql = ("insert into mtr_node(mtr_index, idx, node, loss, snt, last, "
           "ave, best, wrst, stdev)"
           "values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
    val = (mid, idx, node, loss, snt, last, ave, best, wrst, stdev)
    return insert_db(sql, val)


def insert_mtr_node_ip(mtr_node_id, ip):
    sql = "insert into mtr_node_ip(mtr_node_id, node) values(%s, %s)"
    val = (mtr_node_id, ip)
    return insert_db(sql, val)


reMCmd = re.compile('mtr\s([\w\-]+)\s+([\w\.\-]+)')
reMStart = re.compile('Start:\s+([\d\-:]+)T([\d:]+)([+\-]\d+)')
reMHost = re.compile('HOST:\s+([\w\-]+)\s+.*')
reMNode = re.compile(
    '\s+(\d+)\..*\s+([\d\.]+)\s+([\d\.]+)%\s+(\d+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)')
reMNode2 = re.compile(
    '\s+(\d+)\..*\s+(\?+)\s+([\d\.]+)\s+(\d+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)')
reMNodeOnly = re.compile('\s+([\d\.]+).*')

# ttp_code:000,time_namelookup:0.000000,time_connect:0.000000,speed_download:0,time_appconnect:0.000000,time_starttransfer:0.000000,time_total:0.016776
reCurH = re.compile('curl.*max-time\s+\d+\s+([\w\.:/]+)')
reCur = re.compile(
    'http_code:(\d+),time_namelookup:([\d\.]+),time_connect:([\d\.]+),speed_download:([\d\.]+),time_appconnect:([\d\.]+),time_starttransfer:([\d\.]+),time_total:([\d\.]+)')


def get_cur_id(dir, name, host_index):
    sql = (f"SELECT id from curl "
           f"where dir='{dir}' and name='{name}' and host_index='{host_index}'")
    # print(sql)
    cursor.execute(sql)
    if cursor.rowcount:
        r = cursor.fetchone()[0]
        return r
    else:
        return 0


def insert_cur_node(ifconfig, dateid, dir, name, host_index, curName,
                    http_code, time_namelookup, time_connect,
                    speed_download, time_appconnect, time_starttransfer, time_total):
    sql = ("insert into curl(ifconfig, dateid, dir, name, host_index, url, "
           "http_code, time_namelookup, "
           "time_connect, speed_download, time_appconnect, time_starttransfer, time_total) "
           "values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
    val = (' '.join(ifconfig), dateid, dir, name, host_index, curName, http_code, time_namelookup, time_connect, speed_download,
           time_appconnect, time_starttransfer, time_total)
    # Insert this temporary check at line 134
    for i, item in enumerate(val):
        if isinstance(item, (tuple, list)):
            print(f"!!! Error found at index {i}: Element is a {type(item)} -> {item}")

    # print(sql)
    # print(val)
    return insert_db(sql, val)


def insert_cur_result(dir, cur_fname, host_index, ifconfig):
    # print("insert_cur_result")
    # name is dateid
    lines = read_file(dir, cur_fname)
    node_count = 0
    curName = ''
    for l in lines:
        # print(l.strip())
        m = reCurH.match(l.strip())
        if m:
            curName = m.group(1)
            # print(f"curName {curName}")
            continue
        m = reCur.match(l.strip())
        if m:
            print(f"cur {m.group(1)}, {m.group(2)}, {m.group(3)}, {m.group(4)}, {m.group(5)},"
                  f"{m.group(6)}, {m.group(7)}")
            if curName:
                path = Path(dir)
                dateid = path.name
                cid = insert_cur_node(ifconfig, dateid, dir, cur_fname, host_index, curName,
                                      m.group(1), m.group(2), m.group(3), m.group(4),
                                      m.group(5), m.group(6), m.group(7))
                node_count += 1
            else:
                print("curl http error " + l.strip())
    return node_count


def insert_mtr(ifconfig, dir, name, host_index, host, mtr_option, dest, start1, start2, tz, dateid):
    sql = ("insert into mtr(ifconfig, dir, name, host_index, host,"
           "mtr_option, dest, start_date, "
           "start_time, tz, dateid) "
           "values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
    val = (' '.join(ifconfig), dir, name, host_index, host, mtr_option, dest, start1, start2, tz, dateid)
    return insert_db(sql, val)


def insert_mtr_result(dir, name, host_index, ifconfig):
    lines = read_file(dir, name)
    cmdOpt = cmdIP = cmdStart1 = cmdStart2 = cmdTz = cmdHost = ''
    mid = 0

    node_count = 0
    znode_id = 0
    for l in lines:
        m = reMCmd.match(l)
        if m:
            print(f"cmd {m.group(1)}, {m.group(2)}")
            cmdOpt = m.group(1)
            cmdIP = m.group(2)
        m = reMStart.match(l)
        if m:
            print(f"Start {m.group(1)}, {m.group(2)}, {m.group(3)}")
            cmdStart1 = m.group(1)
            cmdStart2 = m.group(2)
            cmdTz = m.group(3)
        m = reMHost.match(l)
        if m:
            # Host is appered in the file after mtr complete
            # during mtr, mtr is not inserted.
            print(f"Host {m.group(1)}")
            cmdHost = m.group(1)
            mdate = cmdStart1.split('-')
            mtime = cmdStart2.split(':')
            d = datetime.datetime(int(mdate[0]), int(mdate[1]), int(mdate[2]),
                                  int(mtime[0]), int(mtime[1]), int(mtime[2]))

            dateid = d.strftime('%Y%m%d%H%M%S')
            print(dateid)
            mid = insert_mtr(ifconfig, dir, name, host_index, cmdHost,
                             cmdOpt, cmdIP, cmdStart1, cmdStart2, cmdTz, dateid)
            print(mid)
        m = reMNode.match(l)
        if m:
            print(
                f"Node {m.group(1)}, {m.group(2)}, {m.group(3)}, {m.group(4)}, {m.group(5)}, {m.group(6)}, {m.group(7)}, {m.group(8)}, {m.group(9)}")
            znode_id = insert_mtr_node(mid, {m.group(1)}, {m.group(2)}, {m.group(3)}, {m.group(4)}, {m.group(5)},
                                       {m.group(6)},
                                       {m.group(7)}, {m.group(8)}, {m.group(9)})
            node_count += 1
            continue
        m = reMNode2.match(l)
        if m:
            print(
                f"Node2 {m.group(1)}, {m.group(2)}, {m.group(3)}, {m.group(4)}, {m.group(5)}, {m.group(6)}, {m.group(7)}, {m.group(8)}, {m.group(9)}")
            znode_id = insert_mtr_node(mid, {m.group(1)}, {m.group(2)}, {m.group(3)}, {m.group(4)}, {m.group(5)},
                                       {m.group(6)},
                                       {m.group(7)}, {m.group(8)}, {m.group(9)})
            node_count += 1
            continue
        print(l)
        m = reMNodeOnly.match(l)
        if m:
            print("NodeOnly")
            print(f"{m.group(1)}")
            print(znode_id)
            insert_mtr_node_ip(znode_id, m.group(1))

    return node_count


def read_file(dir, file):
    with open(join(dir, file)) as f:
        lines = f.readlines()
        return lines if lines else ""


# reSme = re.compile(r'.*The\s+Zscaler\s+hostname\s+for\s+this\s+proxy\s+appears\s+to\s+be\s+\<span\s+class="detailOutput"\>([\w\-]+)\<.*')
reSme = re.compile(
    r'.*The\s+Zscaler\s+hostname\s+for\s+this\s+proxy\s+appears\s+to\s+be\s+\<span\s+class="detailOutput"\>([\w\-]+)\<.*')


# insert infor. of a leaf dir.
# prefix is the result file prefix ("mtr-", "cur-"), get_id/insert_result are
# the matching per-command lookup and inserter.
def insert_leaf_dir(dir, prefix, get_id, insert_result):
    print(f"--- insert_leaf_dir {dir}")
    onlyfiles = [f for f in listdir(dir) if isfile(join(dir, f))]
    flag = 0
    hostname = ''
    hostname_ip = ''
    ipzscaler = ''
    ifconfig = ''
    sme = ''
    for f in onlyfiles:
        match f:
            case "hostname.txt":
                hostname = read_file(dir, "hostname.txt")
                # print(f"hostanme ${hostname}")
                if hostname:
                    hostname = hostname[0].rstrip()
                    flag |= 1
            case "hostname_ip.txt":
                hostname_ip = read_file(dir, "hostname_ip.txt")
                # print(f"hostanme_ip ${hostname_ip}")
                if hostname_ip:
                    hostname_ip = hostname_ip[0].rstrip()
                    flag |= 2
            case "ipzscaler.txt":
                ipzscaler = read_file(dir, "ipzscaler.txt")
                # print(f"ipzscaler ${ipzscaler}")
                for l in ipzscaler:
                    # print(l)
                    m = reSme.match(l)
                    if m:
                        sme = m.group(1)
                        print(f"sme = {sme}")
                        flag |= 4
            case "ifconfig.txt":
                ifconfig = read_file(dir, "ifconfig.txt")
                # print(f"ifpconfig {ifconfig}")
                if ifconfig:
                    flag |= 8
            case _:
                if f.startswith(prefix):
                    # destip = f.replace(prefix, "").replace(".txt", "")
                    # print(f"{destip}")
                    flag |= 16
        # print(f)
    print(f"flag {flag}")
    if flag == 31:
        # all files are ready
        print(f"all ready {hostname}, {hostname_ip}, {sme}")
        hid = insert_or_get_host_index(hostname, hostname_ip, sme, ipzscaler)
        print(hid)
        for f in onlyfiles:
            if f.startswith(prefix):
                name = f.replace(prefix, "").replace(".txt", "")
                # print(f"{destip}")
                r = get_id(dir, f, hid)
                # print(dir, name, hid, r
                if r == 0:
                    r = insert_result(dir, f, hid, ifconfig)
                    if r > 0:
                        # db.rollback()
                        db.commit()
                    else:
                        db.rollback()


# insert infor. of  mtr dir
def insert_mt(dir, dateid):
    insert_leaf_dir(dir, "mtr-", get_mtr_id, insert_mtr_result)


def insert_cur(dir, dateid):
    insert_leaf_dir(dir, "cur-", get_cur_id, insert_cur_result)


functions = {
    "insert_mt": insert_mt,  # mt.  not mtr
    "insert_cur": insert_cur,
}


def find_leaf_dir(dir, dateid, func_name):
    # print(f"find_leaf_dir {dir}")
    onlyfiles = [f for f in listdir(dir) if isfile(join(dir, f))]
    onlydirs = [f for f in listdir(dir) if isdir(join(dir, f))]
    if onlyfiles and not onlydirs:
        print(dir)
        functions[func_name](dir, dateid)

    else:
        for d in onlydirs:
            if d.isnumeric():
                if dateid <= int(d):
                    find_leaf_dir(join(dir, d), dateid, func_name)
            else:
                find_leaf_dir(join(dir, d), dateid, func_name)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    cmd = sys.argv[1]
    match (cmd):
        case "insert":
            mypath = os.path.abspath(sys.argv[2])
            print(mypath)
            if len(sys.argv) > 3:
                find_leaf_dir(mypath, int(sys.argv[3]), "insert_mt")
            else:
                find_leaf_dir(mypath, 0, "insert_mt")
        case "insert_cur":
            mypath = os.path.abspath(sys.argv[2])
            print(mypath)
            if len(sys.argv) > 3:
                find_leaf_dir(mypath, int(sys.argv[3]), "insert_cur")
            else:
                find_leaf_dir(mypath, 0, "insert_cur")

        case "host_list":
            hlist = get_host_list()
            for h in hlist:
                print(h)
        case "get_route" if len(sys.argv) > 2:
            startdate = sys.argv[2]
            enddate = sys.argv[3] if len(sys.argv) > 3 else datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            filename = sys.argv[4] if len(sys.argv) > 4 else f"output_route_{startdate}-{enddate}.xlsx"
            host_dict = get_host_dict()
            # mtr list host_index -> [mtr.id, host, mtr_option, dest, start_date, start_time]
            mtr_list = get_mtr_id_by_daterange(startdate, enddate)
            writer = pd.ExcelWriter(filename)
            f = [['start date', startdate, 'end date', enddate]]
            f2 = [['start date', startdate, 'end date', enddate]]  # only route count
            f2 += [['host', 'sme', 'IP', 'route count']]
            # route check

            for host_index in sorted(mtr_list.keys()):  # key is host_index

                # print(f"m = {host_index}")
                # print(mtr_list[host_index])
                # check path per (host - dest)
                # hostname , sme
                f += [[host_dict[host_index][0], host_dict[host_index][2]]]

                mtr_by_dest = {}
                for mtr_list_by_host in mtr_list[host_index]:  # same host, severl dest
                    # mtr results in 1 host
                    # print(mtr_list_by_host)
                    dest = mtr_list_by_host[3]  #
                    dest_route = Dest_Routes(host_dict[host_index][0], host_dict[host_index][2], dest)
                    print(f"dest {dest}")
                    if dest in mtr_by_dest.keys():
                        # if already exist, replace with old one
                        # disregard newly created dest_route
                        dest_route = mtr_by_dest[dest]
                    else:
                        # print("new dest_route")
                        # dest_route = Dest_Routes(host_dict[host_index][0], host_dict[host_index][2], dest)
                        mtr_by_dest[dest] = dest_route

                    ## get mtr info from mysql
                    nodes = get_mtr_nodes_by_mtrid(mtr_list_by_host[0])

                    # 1 node
                    # 0:idx,1:node,2:loss,3:snt,4:last,5:ave,best,wrst,stdev

                    # create Route_1 with 1st node  (1 route)
                    route_1_temp = Route_1(nodes[0][5], nodes[0][1])
                    # each node after 2nd node
                    for n in nodes[1:]:
                        route_1_temp.append_and_check_loss_lat(n[1], n[2], n[5])
                    ##

                    # search the same route
                    if dest_route.route is None:
                        dest_route.route = [(route_1_temp.route, 1, 0)]
                    else:
                        # print(len(dest_route.route))
                        newFlag = True
                        for i in range(len(dest_route.route)):
                            # for i, r in enumerate(dest_route.route):
                            r = dest_route.route[i]
                            # print("-----")
                            # print(r[0])
                            # print(route_1_temp.route)
                            print(r[0])
                            print(route_1_temp.route)
                            if r[0] == route_1_temp.route:  # compare route
                                # same route
                                c = r[1] + 1
                                print(f"same {c}, {r[2]}")
                                # print(dest_route.route)
                                dest_route.route[i] = (r[0], c, r[2])  # route, count, possible count
                                # print(dest_route.route)
                                newFlag = False
                                break
                            else:
                                print("not same")
                                # check if almost same route
                                # check if it contains "???"
                                route1 = np.array(r[0])
                                route2 = np.array(route_1_temp.route)
                                diff1 = np.setdiff1d(route1, route2)
                                diff2 = np.setdiff1d(route2, route1)
                                print(diff1.tolist())
                                print(diff2.tolist())
                                diff = diff1.tolist() + diff2.tolist()
                                if len(diff) == 1:
                                    print(f"diff = {diff}")
                                    c = r[2] + 1
                                    dest_route.route[i] = (r[0], r[1], c)
                                    print(dest_route.route)
                                    # exit()
                        # print(f"end {newFlag}")
                        if newFlag:
                            dest_route.route.append((route_1_temp.route, 1, 0))
                        # mtr_by_dest[dest] = dest_route

                    # update loss and lat on the same dest
                    dest_route.update_loss_lat(route_1_temp)

                    # print(route)
                    # exit()

                # print(mtr_by_dest)
                for dest in mtr_by_dest.keys():
                    dest_route = mtr_by_dest[dest]
                    f2 += [[host_dict[host_index][0], host_dict[host_index][2],
                            dest, len(dest_route.route)]]

                    f += [['', 'dest', dest,
                           'max - min duration',
                           dest_route.max_duration - dest_route.min_duration,
                           'route count', len(dest_route.route)]]

                    f += [['', 'min duration', dest_route.min_duration,
                           'min lat', dest_route.min_lat_of_min_duration,
                           'max lat', dest_route.max_lat_of_min_duration]]
                    f += [['', 'max duration', dest_route.max_duration,
                           'min lat', dest_route.min_lat_of_max_duration,
                           'max lat', dest_route.max_lat_of_max_duration]]

                    l = ['', 'loss_95_99 node, count']
                    if len(dest_route.loss_95_99) == 0:
                        l += ['0']
                    else:
                        for loss_node in dest_route.loss_95_99.keys():
                            l += [loss_node, dest_route.loss_95_99[loss_node]]
                    f += [l]
                    l = ['', 'loss_90_95 node, count']
                    if len(dest_route.loss_90_95) == 0:
                        l += ['0']
                    else:
                        for loss_node in dest_route.loss_90_95.keys():
                            l += [loss_node, dest_route.loss_90_95[loss_node]]
                    f += [l]
                    for r in dest_route.route:
                        f += [['', 'route count', r[1], 'route count', r[2], 'route'] + r[0]]

            df = pd.DataFrame(f)
            df.to_excel(writer, sheet_name=f"route", index=False, header=False)

            df = pd.DataFrame(f2)
            df.to_excel(writer, sheet_name=f"route count", index=False, header=False)


            # high loss node
            def lost_output(l1, l2):
                f = [[]]
                for host_index in sorted(mtr_list.keys()):  # key is host_index
                    node_list = get_node_lost(host_index, startdate, enddate, l1, l2)
                    print(f"{host_dict[host_index][0]} - len = {len(node_list)}")
                    f += [[host_dict[host_index][0], host_dict[host_index][2]]]
                    for n in node_list:
                        print(n)
                        f += [list(n)]
                    f += [[]]
                df = pd.DataFrame(f)
                df.to_excel(writer, sheet_name=f"lost_{l1}-{l2}"[:31], index=False, header=False)


            lost_output("95.0", "99.9999999")
            lost_output("90.0", "99.9999999")
            writer.close()

        case "get_mtr" if len(sys.argv) > 2:
            startdate = sys.argv[2]
            # enddate = sys.argv[3] if len(sys.argv) > 3 else datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            # filename = sys.argv[4] if len(sys.argv) > 4 else f"output_{startdate}-{enddate}.xlsx"
            print(startdate)
            parser = argparse.ArgumentParser()
            parser.add_argument('-enddate')
            parser.add_argument('-filename')
            parser.add_argument('-sme')
            args = parser.parse_args(sys.argv[3:])

            sheet = get_mtr(startdate, args.enddate, args.sme)
            # print(sheet)
            # hlist = get_host_list()
            # host_dict={}
            # for h in hlist:
            #     host_dict[h[0]] = h[1:]
            # mtr_list = get_mtr_id_by_daterange(startdate, enddate)
            # writer = pd.ExcelWriter(filename)
            # print(mtr_list.keys())
            # for host_index in sorted(mtr_list.keys()):  # key is host_index
            #     print(f"m = {host_index}")
            #     # print(mtr_list[host_index])
            #
            #     f = [['DEST IP', 'date', '', 'option', 'sme']]
            #     for mtr_list_by_host in mtr_list[host_index]:  # mtr list with host_index=m
            #         #each mtr
            #         nl = []
            #         print(f"mtr id= {mtr_list_by_host[0]}")
            #         f += [[mtr_list_by_host[3],  mtr_list_by_host[4],mtr_list_by_host[5],mtr_list_by_host[2]]]
            #         f += [['HOST:', '', 'Loss%','Snt','Last','Avg','Best','Wrst','StDev']]
            #         nodes = get_mtr_nodes_by_mtrid(mtr_list_by_host[0])
            #
            #
            #         for n in nodes:
            #             # print(f"n = {n}")
            #             f += [list(n)]
            #
            #             # high latency
            #             # min and max in the route
            #
            #
            #
            #         f += [[]]
            filename = args.filename if args.filename \
                else f"output_{startdate}-{args.enddate}.xlsx"
            print(filename)
            writer = pd.ExcelWriter(filename)
            print(len(sheet.keys()))
            for key in sorted(sheet.keys()):
                # print(sht, len(sht[2]))
                f = sheet[key]
                df = pd.DataFrame(f)
                v = key.split(':')
                df.to_excel(writer, sheet_name=f"{v[0].replace('IPSec', '').replace('ZS3', '')[:4]}-{v[1]}"[:31],
                            index=False, header=False)
            writer.close()

        # case "ana" :
        #     # pcap_index
        #     stream(sys.argv[2])
        case "get_mtr2" if len(sys.argv) > 2:
            startdate = sys.argv[2]
            # enddate = sys.argv[3] if len(sys.argv) > 3 else datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            # filename = sys.argv[4] if len(sys.argv) > 4 else f"output_{startdate}-{enddate}.xlsx"
            print(startdate)
            parser = argparse.ArgumentParser()
            parser.add_argument('-edate')
            parser.add_argument('-filename')
            parser.add_argument('-sme')
            parser.add_argument('-list')
            args = parser.parse_args(sys.argv[3:])

            print('getcwd:      ', os.getcwd())
            print('__file__:    ', __file__)
            print('basename:    ', os.path.basename(__file__))
            print('dirname:     ', os.path.dirname(__file__))
            print('dirname list:     ', os.path.dirname(args.list)) if args.list else "."

            dest_list = []
            # with open(os.path.join(os.getcwd() ,args.list)) as f:
            if args.list:
                with open(args.list) as f:
                    for line in f:
                        dest_list += [line.strip()]
            print(dest_list)

            sheet = get_mtr(startdate, args.edate, args.sme, dest_list)
            filename = args.filename if args.filename \
                else f"output_{startdate}-{args.edate}-{args.sme if args.sme else ''}.xlsx"
            print(filename)
            writer = pd.ExcelWriter(filename)
            print(len(sheet.keys()))
            for key in sorted(sheet.keys()):
                # print(sht, len(sht[2]))
                f = sheet[key]
                df = pd.DataFrame(f)
                v = key.split(':')
                df.to_excel(writer, sheet_name=f"{v[0].replace('IPSec', '').replace('ZS3', '')[:4]} {v[1]}"[:31],
                            index=False, header=False)
            writer.close()
        case "get_cur" if len(sys.argv) > 2:
            startdate = sys.argv[2]
            parser = argparse.ArgumentParser()
            parser.add_argument('-edate')
            parser.add_argument('-filename')
            args = parser.parse_args(sys.argv[3:])


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
