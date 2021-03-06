import argparse
import ipaddress
import json
import os
import socket
import sys
import time
import warnings
from pprint import pprint

import shodan
from ipwhois import IPWhois

warnings.filterwarnings("ignore")

cache = {}
shodanCache = {}

parser = argparse.ArgumentParser()
parser.add_argument(
    "dnslist", help="A text file containing a list of domain names")
parser.add_argument("-s",
                    "--shodan", default=True, action="store_false", help="Disable Shodan search against discovered IP addresses")
parser.add_argument("-c",
                    "--config", default=f"{os.path.dirname(os.path.realpath(__file__))}/config.json", help="Provide a config file containing API keys for additional services (e.g. Shodan)")
parser.add_argument("-d",
                    "--delim", default="\t", help="Output delimiter (default is tab)")
args = parser.parse_args()
shodan_enable = args.shodan
delim = args.delim

if shodan_enable:
    try:
        with open(args.config, "r") as f:
            config = json.load(f)
            SHODAN_APIKEY = config["shodan"]
            shodan_enable = True
        api = shodan.Shodan(SHODAN_APIKEY)
    except FileNotFoundError as e:
        print(f"Config file doesn't exist. A sample file is included in the repository for this project. {e}")
        shodan_enable = False
        sys.exit(1)
    except KeyError:
        print(f"malformed config file - missing shodan api key")
        shodan_enable = False
        sys.exit(1)
    except Exception as e:
        print(f"Um this is well fucked eh: {e}")
        shodan_enable = False
        sys.exit(1)


def searchCache(ip):
    result = False

    for item in cache.keys():
        needle = ipaddress.ip_network(f'{ip}/32')
        haystack = ipaddress.ip_network(item)
        if (needle.subnet_of(haystack)):
            result = cache[item]

    return result


def searchIP(ip):
    # first we will need to search cache
    result = searchCache(ip)
    if (result == False):
        try:
            obj = IPWhois(ip)
            result = obj.lookup_rdap(depth=1)
            if result["asn_cidr"] != "NA":
                cache[result["asn_cidr"]] = result
            else:
                cache[result["network"]["cidr"]] = result
        except:
            return "Failed"

    return result


def getIP(d):
    """
    returns thinger of
    one or more IP address strings that respond
    as the given domain name
    """
    try:
        data = socket.gethostbyname_ex(d)
        ipx = data[2]
        return ipx
    except Exception:
        # fail gracefully!
        return False
#


def getRDNS(ip):
    """
        gets rdns, idk what you expect
    """
    try:
        data = socket.gethostbyaddr(ip)
        host = data[0]
        return host
    except Exception:
        # fail gracefully
        return "None"
#


def getCNAME(d):
    """
    This method returns an array containing
    a list of cnames for the domain
    """
    try:
        data = socket.gethostbyname_ex(d)
        alias = repr(data[1])
        return alias
    except Exception:
        # fail gracefully
        return False


def getIPOwner(ip):
    try:
        results = searchIP(ip)
        return results["network"]["name"]
    except:
        return "No Data/Failed"


def getIPHoster(ip):
    try:
        results = searchIP(ip)
        return results["asn_description"]
    except:
        return "No Data/Failed"


def getWhoisCIDR(ip):
    try:
        results = searchIP(ip)
        return results["asn_cidr"]
    except:
        return "No Data/Failed"


def getBGPCIDR(ip):
    try:
        results = searchIP(ip)
        return results["network"]["cidr"]
    except:
        return "No Data/Failed"


def getASN(ip):
    try:
        results = searchIP(ip)
        return results["asn"]
    except:
        return "No Data/Failed"


def shodan_search(ip):
    if ip in shodanCache.keys():
        return shodanCache[ip]
    else:
        try:
            host = api.host(ip)
            shodanCache[ip] = host
        except shodan.APIError:
            return None
        return host


def getShodanPorts(host):
    try:
        ports = (f'{item["port"]}({item["_shodan"]["module"]})' for item in host["data"])
        return ",".join(ports)
        # return ", ".join(map(str, ports))
    except:
        return "No Data/Failed"


domains = [line.rstrip('\n') for line in open(args.dnslist)]
if shodan_enable:
    print(f'IP{delim}DNS{delim}RDNS{delim}ASN{delim}IP Hoster{delim}IP Owner{delim}BGP CIDR{delim}Whois CIDR{delim}Shodan Ports')
else:
    print(f'IP{delim}DNS{delim}RDNS{delim}ASN{delim}IP Hoster{delim}IP Owner{delim}BGP CIDR{delim}Whois CIDR')

for domain in domains:
    time.sleep(0.01)
    data = getIP(domain)
    if data != False:
        for ip in data:
            # try:
            if shodan_enable:
                host = shodan_search(ip)
                print(f'"{ip}"{delim}"{domain}"{delim}"{getRDNS(ip)}"{delim}"{getASN(ip)}"{delim}"{getIPHoster(ip)}"{delim}"{getIPOwner(ip)}"{delim}"{getBGPCIDR(ip)}"{delim}"{getWhoisCIDR(ip)}"{delim}"{getShodanPorts(host)}"')
            else:
                print(f'"{ip}"{delim}"{domain}"{delim}"{getRDNS(ip)}"{delim}"{getASN(ip)}"{delim}"{getIPHoster(ip)}"{delim}"{getIPOwner(ip)}"{delim}"{getBGPCIDR(ip)}"{delim}"{getWhoisCIDR(ip)}"')
            # except:
            #    sys.stderr.write(f'Error:{ip} failed for some reason')
            #    pass
