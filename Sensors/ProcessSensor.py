import psutil
import pandas as pd
import numpy as np
import pefile
import pickle
import requests
import json
import os
import time
import random
import configparser
from urllib.parse import urlparse
# from signify.authenticode import SignedPEFile

import pdb

# This is needed for the exe compilation
# Makes sure the exe gets the correct path for the authroot.stl file, otherwise the exe will crash
def getActualPath():
    return os.path.abspath("authroot.stl")


# if network connection == 20.187.93.224 then display <-- hardcoded ip
# [Services.exe, Hong Kong, 20.187.93.224], 
# [lsass.exe, Russian federation, 185.161.248.151], 
# [w3wp.exe, Venezuela (Bolivarian Republic of),179.60.147.143]
# AsyncRat path: C:\Users\MyAcc\Downloads\AsyncRemoteAdmin/Stub/Stub.exe

# Have processes resync on the subset of our test processes faster than other processes

#--------------
# Read the config file
#--------------
def ConfigFileReader():
    config_file = configparser.ConfigParser()
    config_file.read("D:\\Documents\\TaskManager\\TaskManager\\sensor.config")
    # Each section in the config file is one rule
    #for section in config_file.sections():
        # Get rule information, store them and then apply it
        #for (key, value) in config_file.items(section):
            #print(section)
            #print(key)
            #print(value)
    # line = config_file.readlines()
    # print(line)
    return config_file


class ProcessSensor():
    def __init__(self):
        #self.ps = None
        self.cpus = psutil.cpu_count()
        self.procs = dict()
        self.df = None
        self.files = dict()
        self.connections = dict()
        #self.verifier = False
        self.connections_cache, self.connections_cache_dirty = dict(), False
        self.verifier_cache, self.verifier_cache_dirty = dict(), False
        #self.get_ps_list()

        # This is for the study only, a way to override the values shown via config
        # Remove for the full version presumably
        self.configs = ConfigFileReader()
        self.overriddenValues = {}
        

        if os.path.isfile('conn_cache.pkl'):
            with open('conn_cache.pkl', 'rb') as f:
                self.connections_cache = pickle.load(f)

        if os.path.isfile('verifier_cache.pkl'):
            with open('verifier_cache.pkl', 'rb') as f:
                self.verifier_cache = pickle.load(f)

    def get_ps_list(self):
        return psutil.pids()

    def get_process_counters(self, pid):
        try:
            self.procs[pid] = psutil.Process(pid)

            vals = list()
            vals.append(pid)
            with self.procs[pid].oneshot():
                try:
                    vals.append(self.procs[pid].name())
                except Exception as exception:
                    vals.append(exception.__class__.__name__)

                try:
                    vals.append(self.procs[pid].exe())
                except Exception as exception:
                    vals.append(exception.__class__.__name__)

                try:
                    #print(self.procs[pid].create_time())
                    # print(time.localtime(self.procs[pid].create_time()) )
                    # vals.append(time.strftime("%H:%M:%S", time.localtime(self.procs[pid].create_time())))
                    vals.append(time.localtime(self.procs[pid].create_time()))
                except Exception as exception:
                    vals.append(exception.__class__.__name__)

                try:
                    vals.append(self.procs[pid].ppid())
                except Exception as exception:
                    vals.append(exception.__class__.__name__)
                try:
                    vals.append(self.procs[pid].status())
                except Exception as exception:
                    vals.append(exception.__class__.__name__)

                try:
                    # reset the process saved so that cpu_percent has a comparison to do
                    # self.procs[pid] = psutil.Process(pid)
                    # cpu_check = self.procs[pid].cpu_percent()
                    #print(cpu_check)
                    # noInfinite = 0
                    # while cpu_check == 0.0 and noInfinite < 51:
                    #     time.sleep(0.1)
                    #     cpu_check = self.procs[pid].cpu_percent()
                    #     noInfinite += 1
                    # print(cpu_check)
                    vals.append(self.procs[pid].cpu_percent())
                    # vals.append(8)
                except Exception as exception:
                    vals.append(exception.__class__.__name__)

                try:
                    memory = self.procs[pid].memory_info()
                    # rss: aka “Resident Set Size”, this is the non-swapped physical memory a process has used.
                    vals.append(int(memory.rss / 1000000))
                except Exception as exception:
                    vals.append(exception.__class__.__name__)

                try:
                    io_ctr = self.procs[pid].io_counters()
                    vals.append(int(io_ctr.read_bytes / 1000000))
                    vals.append(int(io_ctr.write_bytes / 1000000))
                except Exception as exception:
                    vals.append(exception.__class__.__name__)
                    vals.append(exception.__class__.__name__)
                try:
                    vals.append(self.procs[pid].cmdline())
                except Exception as exception:
                    vals.append(exception.__class__.__name__)
            return vals
        except Exception as exception:
            vals = list()
            vals.append(exception.__class__.__name__)
            return vals

    def init_process_counters(self):
        self.df = pd.DataFrame(columns=['pid', 'Process', 'exe', 'Create Time', 'ppid', 'status', 'CPU (%)',
                                   'Memory (MB)', 'Disk Read (MB)', 'Disk Write (MB)', 'cmd'])
        ps = self.get_ps_list()
        for pid in ps:
            if not psutil.pid_exists(pid):
                continue
            vals = self.get_process_counters(pid)
            self.df.loc[len(self.df)] = vals

        self.df.set_index('pid', inplace=True)
        self.df['Network Connections'] = 'Loading...'
        self.df['Files'] = 'Loading...'
        self.df['Verified Publisher'] = 'Loading...'

    def update_process_counters(self):
        #status, cpu, memory, disk_in, disk_out = list(), list(), list(), list(), list()
        cur_pids = set(psutil.pids())
        reg_pids = set(self.df.index)
        new_procs = list(cur_pids - reg_pids)
        for pid in new_procs:
            vals = self.get_process_counters(pid)
            del vals[0]
            
            # set up early process for comparison with cpu_percent
            self.procs[pid] = psutil.Process(pid)
            cpu_check = self.procs[pid].cpu_percent()

            # Search for the correct file location
            # if the file location is found
            # manually replace the values
            randomized = False
            # ['WmiPrvSE.exe', 'C:\\Windows\\System32\\wbem\\WmiPrvSE.exe', 1684461764.1019304, 1252, 'running', 0.0, 11, 0, 0, 'AccessDenied', '', '', 'Microsoft Corporation']
            #print(vals)
            name = self.procs[pid].name()
            if self.configs:
                #Search the sections of the config
                for section in self.configs.sections():
                    # For the sections titled ip, get the relevent information
                    # If the section has been "chosen" already, skip all this and just assign the correct values
                    if section.startswith("IP_") and name not in self.overriddenValues:
                        # If this is a new rule in a new section, add the name of the section and the generated value to be reused
                        for (key, value) in self.configs.items(section):
                            
                            if key == "path" and vals[1] == value:
                                # async rat 1 is hardcoded to HOng Kong
                                # async rat 2 is hardcoded to Russian Federation
                                # async rat 3 is hardcoded to Venezuala 
                                
                                if name == 'lsass.exe':
                                    self.overriddenValues[name] = "Connections to: Hong Kong"
                                    vals.append("Connections to: Hong Kong")
                                    randomized = True
                                elif name == 'servcies.exe': 
                                    vals.append("Connections to: Russian Federation")
                                    vals.append("Connections to: Russian Federation")
                                    randomized = True
                                elif name == 'w3wp.exe':
                                    vals.append("Connections to: Venezuela")
                                    vals.append("Connections to: Venezuela")
                                    randomized = True
                               
                                # Randomly choose one of three different options to display
                                # choice = random.randrange(1,4)
                                # self.overriddenValues[section] = choice
                                # if choice == 1:
                                # #     vals.append("Connections to: Hong Kong")
                                #     randomized = True
                                # elif choice == 2:
                                #     vals.append("Connections to: Russian Federation")
                                #     randomized = True
                                # else: 
                                #     vals.append("Connections to: Venezuela")
                                #     randomized = True
                    elif name in self.overriddenValues:
                        vals.append(self.overriddenValues[name])
                        randomized = True
                    #elif section in self.overriddenValues:
                        #if self.overriddenValues[section] == 1:
                        #    vals.append("Connections to: Hong Kong")
                        #    randomized = True
                        #elif self.overriddenValues[section] == 2:
                        #    vals.append("Connections to: Russian Federation")
                        #    randomized = True
                        #else: 
                        #    vals.append("Connections to: Venezuela")
                        #    randomized = True

            if not randomized:
                vals.append(self.get_net_connections(pid)) # Network Connections
                
            vals.append(self.get_open_files(pid, vals[1])) # Files
            vals.append(self.get_publisher_name(vals[1])) # Verified Publisher 
            self.df.loc[pid] = vals

        #if len(new_procs) > 0:
        #    self.get_process_counters(new_procs, False)
        for pid, row in self.df.iterrows():
            if not psutil.pid_exists(pid):
                self.df.drop(pid, inplace=True)
                if pid in self.procs:
                    del(self.procs[pid])
                if pid in self.files:
                    del(self.files[pid])
                if pid in self.connections:
                    del (self.connections[pid])
                continue

            with self.procs[pid].oneshot():
                #try:
                #    status.append(self.procs[pid].status())
                #except Exception as exception:
                #    status.append(exception.__class__.__name__)

                try:
                    # print(self.procs[pid].cpu_percent())
                    row['CPU (%)'] = self.procs[pid].cpu_percent()
                    # print(row['CPU (%)'])
                except Exception as exception:
                    row['CPU (%)'] = 0.0

                try:
                    mem = self.procs[pid].memory_info()
                    # rss: aka “Resident Set Size”, this is the non-swapped physical memory a process has used.
                    row['Memory (MB)'] =  int(mem.rss / 1000000.0)
                except Exception as exception:
                    row['Memory (MB)'] =  0

                try:
                    io_ctr = self.procs[pid].io_counters()
                    row['Disk Read (MB)'] = int(io_ctr.read_bytes / 1000000)
                    row['Disk Write (MB)'] = int(io_ctr.write_bytes / 1000000)
                except Exception as exception:
                    row['Disk Read (MB)'] = 0
                    row['Disk Write (MB)'] = 0

            try:
                self.df.loc[pid] = row
            except Exception as e:
                print("there is an error: " + str(e))
                continue
        #if len(terminated) > 0:
        #    self.df.drop(terminated, inplace=True)
        #    for i in range(0, len(terminated)):
        #        if terminated[i] in self.ps:
        #            self.ps.remove(terminated[i])
        #        if terminated[i] in self.procs:
        #            del(self.procs[terminated[i]])
        #self.df['status'] = status
        #self.df['CPU (%)'] = cpu
        #self.df['Memory (MB)'] = memory
        #self.df['Disk Read (MB)'] = disk_in
        #self.df['Disk Write (MB)'] = disk_out

    def get_open_files(self, pid, exe, enriched_files = ''):
        if not psutil.pid_exists(pid):
            return ''
        files = ''
        #if previously logged as AccessDenied
        if pid in self.files:
            if self.files[pid] == 'AccessDenied':
                return ''
        #Get open Files
        try:
            file_fd = self.procs[pid].open_files()
            for f in file_fd:
                if files == '':
                    files += f.path
                else:
                    files = files + ',' + f.path

        except Exception as exception:
            return ''

        #if AccessDenied; store and return
        if files == 'AccessDenied':
            self.files[pid] = files
            return ''



        if pid in self.files:
            if files != self.files[pid]: #was it updated?
                enriched_files = self.enrich_files(files, exe)
        else: #first time
            enriched_files = self.enrich_files(files, exe)
            self.files[pid] = files
        return enriched_files

    def update_open_files(self):
        # for pid, row in self.df.iterrows():
        for pid in self.df.index:
            try:
                enriched_files = self.get_open_files(pid, self.df.at[pid, 'exe'], self.df.at[pid, 'Files'])
                self.df.at[pid, 'Files'] = enriched_files
                #print('updating)
            except:
                continue

    def update_net_connections(self):
        for pid in self.df.index:
            try:
                cons = self.get_net_connections(pid, self.df.at[pid, 'Network Connections'])
                self.df.at[pid, 'Network Connections'] = cons
            except:
                continue
        if self.connections_cache_dirty:
            with open('conn_cache.pkl', 'wb') as f:
                pickle.dump(self.connections_cache, f)
            self.connections_cache_dirty = False

    def get_net_connections(self, pid, enriched_connections = ''):
        if not psutil.pid_exists(pid):
            return ''
        if pid in self.connections:
            if self.connections[pid] == 'AccessDenied':
                return ''
        con_info = ''
        try:
            connections = self.procs[pid].connections()
            for cons in connections:
                if (len(cons)) < 2:
                    return ''
                if len(cons.raddr) == 0:
                    return ''
                if cons.raddr[0] == '127.0.0.1' or cons.raddr[0] == '0.0.0.0':
                    return ''
                if con_info == '':
                    con_info = str(
                        cons.raddr[0])  # XXX: https://psutil.readthedocs.io/en/latest/#connections-constants
                else:
                    con_info = con_info + '\n' + str(cons.raddr[0])
        except Exception as exception:
            self.connections[pid] = ''
            return ''

        if con_info == 'AccessDenied':
            self.connections[pid] = con_info
            return ''


        if pid in self.connections:
            if con_info != self.connections[pid]:
                enriched_connections = self.enrich_network_connections(con_info)
        else:
            enriched_connections = self.enrich_network_connections(con_info)
            self.connections[pid] = con_info

        return enriched_connections

    def update_publisher_names(self):
        for idx in self.df.index:
            try:
                org = self.get_publisher_name(self.df.at[idx, 'exe'])
                self.df.at[idx, 'Verified Publisher'] = org
            except Exception as e:
                continue
        if self.verifier_cache_dirty:
            with open('verifier_cache.pkl', 'wb') as f:
                pickle.dump(self.verifier_cache, f)
            self.verifier_cache_dirty = False

    def get_publisher_name(self, exe):
        if exe != exe:
            return ''
        elif not os.path.exists(exe):
            return ''
        elif exe in self.verifier_cache:
            return self.verifier_cache[exe]
        else:
            org = None
            try:
                pe = pefile.PE(exe)
                if hasattr(pe, "VS_VERSIONINFO"):
                    if hasattr(pe, "FileInfo"):
                        for entries in pe.FileInfo:
                            for entry in entries:
                                if hasattr(entry, 'StringTable'):
                                    for st_entry in entry.StringTable:
                                        for str_entry in st_entry.entries.items():
                                            if b'CompanyName' in str_entry and len((str_entry[1])) > 0:
                                                org = str_entry[1].decode('UTF-8')
            except Exception as e:
                return org
            self.verifier_cache[exe] = org
            self.verifier_cache_dirty = True
            return org

    def enrich_network_connections(self, ip_list_str):
        known_countries = {'Australia', 'Austria', 'Canada', 'Denmark', 'Finland', 'Germany', 'Ireland', 'Japan', 'Norway',
                           'Singapore', 'Sweden', 'Switzerland', 'United Kingdom of Great Britain and Northern Ireland',
                           'United States of America', 'Virgin Islands (British)', 'Virgin Islands (U.S.)'}

        if ip_list_str != ip_list_str: #checks for nan
            return ''
        d = dict()
        d['country'], d['aut_sys'], = dict(), dict()
        con_info = ''
        toks = ip_list_str.split(',')
        for ip in toks:
            # print(ip)
            if ip in self.connections_cache:
                aut_sys, country = self.connections_cache[ip]
            else:
                # try:
                #    resp = socket.gethostbyaddr(ip)
                #    if len(resp) > 1:
                #        domain = urlparse(resp[0]).netloc
                #    else:
                #        domain = None
                # except Exception as e:
                #    domain = None

                aut_sys, country = self.ip2loc(ip)
                if aut_sys != None:
                    self.connections_cache[ip] = aut_sys, country
                    self.connections_cache_dirty = True
            # d['domain'][domain] = d['domain'][domain] + 1 if domain in d['domain'] else 1
            if country != None:
                d['country'][country] = d['country'][country] + 1 if country in d['country'] else 1
            if aut_sys != None:
                d['aut_sys'][aut_sys] = d['aut_sys'][aut_sys] + 1 if aut_sys in d['aut_sys'] else 1
        countries = d['country'].keys()
        questionable_countries = countries - known_countries
        if len(questionable_countries) > 0:
            for country in questionable_countries:
                con_info = 'Connections to: ' + country + ','
            con_info = con_info[:-1]
        elif len(d['aut_sys'].keys()) > 0:
            con_info = 'Connections to: ' + str(d['aut_sys'])[1:-1]
        return con_info

    def ip2loc(self, ip):
        IP2LOCATION_API_KEY = 'E4879D711C8DECF11FB5D23BB78CBEF7'
        #known_as = ['MICROSOFT', 'Microsoft', 'Google', 'Amazon', 'Akamai', 'Bell', 'CloudFlare Inc.']
        response = requests.get('https://api.ip2location.io/?key=' + IP2LOCATION_API_KEY + '&ip=' + ip).text
        dict_resp = json.loads(response)

        #aut_sys = dict_resp['as']
        #for s in known_as:
        #    if dict_resp['as'] in s:
        #        aut_sys = s
        #        break
        #print(ip)
        #print(dict_resp)
        return dict_resp.get('as', None), dict_resp.get('country_name', None)

    # Returns the number of files to display in the table
    def enrich_files(self, file_list_str, exe_path):
        d = dict()
        if not os.path.exists(exe_path):
            return ''
        exe_dir_path = os.path.normcase(os.path.dirname(exe_path))
        toks = file_list_str.split(',')
        d['Total'] = len(toks)
        for fi in toks:
            dir_path = os.path.normcase(os.path.dirname(fi))
            if len(dir_path) < 2: # ~empty string
                continue
            # 1. Eliminate files from the same applications
            if os.path.commonpath([exe_dir_path, dir_path]) == exe_dir_path:
                continue
            # 2. Determine Temp Files
            elif dir_path == 'c:\\windows\\temp' or dir_path.endswith('appdata\\local\\temp') or \
                    dir_path.endswith('\\local settings\\temp'):
                d['Temp'] = d['Temp'] + 1 if 'Temp' in d else 1
            # 3. Ignore fonts etc
            elif dir_path in ['c:\\windows\serviceprofiles\\localservice\\appdata\\local\\fontcache',
                               'c:\\windows\\fonts', 'c:\\windows\\system32\\en-us',
                               'c:\windows\system32\speech']:
                continue
            # 4. Program/App Data
            elif dir_path.endswith('appdata\\local') or dir_path.endswith('appdata\\roaming') or \
                    dir_path.endswith('c:\\documents and settings\\all users\\application data') or \
                    dir_path == 'c:\\programdata':
                d['Program Data'] = d['Program Data'] + 1 if 'Program Data' in d else 1
            # 5. Program Files 'c:\\program files', 'c:\\program files (x86)','c:\\program files (64-bit)','c:\\program files\\common files'
            elif dir_path.startswith('c:\\program files'):
                d['Program Files'] = d['Program Files'] + 1 if 'Program Files' in d else 1
            # 6. Windows 'c:\\windows', 'c:\\windows\\system','c:\\windows\\system32','c:\\windows\\SysWow64',
            #       'C:\Windows\Registration\' ,' C:\Windows\System32\DriverStore\ accesses C:\Windows\assembly\'
            elif dir_path.startswith('c:\\windows'):
                d['Windows'] = d['Windows'] + 1 if 'Windows' in d else 1
            # 7. For AsyncRAT malware hardcode
            # # AsyncRat path: C:\Users\MyAcc\Downloads\AsyncRemoteAdmin/Stub/Stub.exe
            # TODO Get local variable populated by config file
            # Loop through to find values to search for and replace
            # replace table information
            # COnfig file layout? Path || Value[s] to change || Value[s] to change too
            # elif dir_path.startswith('c:\\users\\myacc\\downloads\\asyncremoteadmin\\stub\\stub'):
        #make dictionary printable
        d_str = (str(d))[1:-1]
        return d_str.replace('\'','')

    # Duplicated functions purely for the study, each has an additional check to determine if it is one of the processes for the study
    # self.procs[pid].name()

    def update_net_connections_study(self):
        studyProcs = ['Brothersoft_Driver223_Install.exe', 'creativecloud_cc_64_en_hi_gocd_mdr_install.exe', 'lsass.exe', 'servcies.exe', 'w3wp.exe', 'SHAREit-KCWEB.exe', 'FrostWire.exe', 'DriverEasy_Setup.exe', 'DiskCleaner.exe', 'BackgroundCleaner.exe', 'Defragger.exe', 'DiskView.exe', 'CCleaner.exe', 'IV_Player.exe'] 
        studyProcFound = False
        for pid in self.df.index:
            if self.procs[pid].name() in studyProcs:
                studyProcFound = True
                try:
                    cons = self.get_net_connections(pid, self.df.at[pid, 'Network Connections'])
                    self.df.at[pid, 'Network Connections'] = cons
                except:
                    continue
        if studyProcFound:
            if self.connections_cache_dirty:
                with open('conn_cache.pkl', 'wb') as f:
                    pickle.dump(self.connections_cache, f)
                self.connections_cache_dirty = False

    def update_open_files_study(self):
        studyProcs = ['Brothersoft_Driver223_Install.exe', 'creativecloud_cc_64_en_hi_gocd_mdr_install.exe', 'lsass.exe', 'servcies.exe', 'w3wp.exe', 'SHAREit-KCWEB.exe', 'FrostWire.exe', 'DriverEasy_Setup.exe', 'DiskCleaner.exe', 'BackgroundCleaner.exe', 'Defragger.exe', 'DiskView.exe', 'CCleaner.exe', 'IV_Player.exe'] 
        # for pid, row in self.df.iterrows():
        for pid in self.df.index:
            if self.procs[pid].name() in studyProcs:
                try:
                    enriched_files = self.get_open_files(pid, self.df.at[pid, 'exe'], self.df.at[pid, 'Files'])
                    self.df.at[pid, 'Files'] = enriched_files
                    #print('updating)
                except:
                    continue

    #def get_authenticode_signer(self, fname):
        #XXX the following code can be used to test that hash is correct; not in use for the demo
    #    verifier_cache = dict()
    #    verifier_list = list()
    #    import pandas as pd
    #    df = pd.read_csv('c:\\wd\\HMD\\TaskManager\\ui\\stats_df')
    #    df['Verifier'] = ''
    #    for idx,row in df.iterrows():
    #        exe = row['exe']
    #        if exe != exe:
    #            df.at[idx, 'Verifier'] = ''
    #        elif not os.path.exists(exe):
    #            df.at[idx, 'Verifier'] = ''
    #        else:
    #            if exe in verifier_cache:
    #                df.at[idx, 'Verifier'] = verifier_cache[exe]
    #            else:
    #                org = None
    #                exe = 'C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe'
    #                with open(exe, 'rb') as f:
    #                    pefile = SignedPEFile(f)
    #                    try:
    #                        for signed_data in pefile.signed_datas:
    #                            for signer_info in signed_data.signer_infos:
    #                                s = signer_info.issuer.dn
    #                                try:
    #                                    org = s[s.index('O=') + 2:].split(',')[0]
    #                                    if org is not None:
    #                                        df.at[idx,'Verifier'] = org
    #                                        verifier_cache[exe] = org
    #                                        verifier_chache_dirty = True
    #                                        print(org)
    #                                        #if not org.lower().startswith('digicert'):
    #                                        #    break
    #                                except Exception as exception:
    #                                    continue
    #                    except Exception as e:
    #                        df.at[idx,'Verifier'] = org
    #                        verifier_cache[exe] = org
    #                if org is None:
    #                    verifier_cache[exe] = org