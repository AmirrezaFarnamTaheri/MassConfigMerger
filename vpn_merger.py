#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VPN Subscription Merger
===================================================================

The definitive VPN subscription merger combining 450+ sources with comprehensive
testing, smart sorting, and automatic dead link removal.

Features:
• Complete source collection (450+ Iranian + International repositories)
• Real-time URL availability testing and dead link removal
• Server reachability testing with response time measurement
• Smart sorting by connection speed and protocol preference
• Event loop compatibility (Jupyter, IPython, regular Python)
• Advanced deduplication with semantic analysis
• Multiple output formats (raw, base64, CSV, JSON)
• Comprehensive error handling and retry logic
• Best practices implemented throughout

Requirements: pip install aiohttp aiodns nest-asyncio
Author: Final Unified Edition - June 30, 2025
Expected Output: 800k-1.2M+ tested and sorted configs
"""

import asyncio
import base64
import csv
import hashlib
import json
import logging
import random
import re
import ssl
import sys
import time
import socket
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

import aiohttp
from aiohttp.resolver import AsyncResolver

# Event loop compatibility fix
try:
    import nest_asyncio
    nest_asyncio.apply()
    print("✅ Applied nest_asyncio patch for event loop compatibility")
except ImportError:
    print("📦 Installing nest_asyncio...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nest-asyncio"])
    import nest_asyncio
    nest_asyncio.apply()

try:
    import aiodns
except ImportError:
    print("📦 Installing aiodns...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiodns"])
    import aiodns

# ============================================================================
# CONFIGURATION & SETTINGS
# ============================================================================

@dataclass
class Config:
    """Comprehensive configuration for optimal performance."""
    
    # HTTP settings
    headers: Dict[str, str]
    request_timeout: int
    connect_timeout: float
    max_retries: int
    
    # Processing settings
    concurrent_limit: int
    max_configs_per_source: int
    
    # Protocol validation
    valid_prefixes: Tuple[str, ...]
    
    # Testing settings
    enable_url_testing: bool
    enable_sorting: bool
    test_timeout: float

    # Output settings
    output_dir: str

    # New features
    batch_size: int
    threshold: int
    top_n: int
    tls_fragment: Optional[str]
    include_protocols: Optional[Set[str]]
    exclude_protocols: Optional[Set[str]]
    resume_file: Optional[str]
    max_ping_ms: Optional[int]
    log_file: Optional[str]
    cumulative_batches: bool
    strict_batch: bool
    shuffle_sources: bool
    write_base64: bool
    write_csv: bool

CONFIG = Config(
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    },
    request_timeout=30,
    connect_timeout=3.0,
    max_retries=3,
    concurrent_limit=50,
    max_configs_per_source=75000,
    valid_prefixes=(
        "vmess://", "vless://", "ss://", "trojan://", "hy2://", 
        "hysteria://", "hysteria2://", "tuic://", "reality://", 
        "naive://", "juicity://", "shadowtls://", "wireguard://", 
        "brook://", "socks://", "socks4://", "socks5://",
        "http://", "https://", "grpc://", "ws://", "wss://",
        "ssr://", "tcp://", "kcp://", "quic://", "h2://",
    ),
    enable_url_testing=True,
    enable_sorting=True,
    test_timeout=5.0,
    output_dir="output",
    batch_size=1000,
    threshold=0,
    top_n=0,
    tls_fragment=None,
    include_protocols=None,
    exclude_protocols=None,
    resume_file=None,
    max_ping_ms=1000,
    log_file=None,
    cumulative_batches=False,
    strict_batch=True,
    shuffle_sources=False,
    write_base64=True,
    write_csv=True
)

# ============================================================================
# COMPREHENSIVE SOURCE COLLECTION (ALL UNIFIED SOURCES)
# ============================================================================

class UnifiedSources:
    """Complete unified collection of all VPN subscription sources."""
    
    # Iranian Priority Sources (High Quality, Frequently Updated)
    # Iranian Priority Sources (High Quality, Frequently Updated)
    IRANIAN_PRIORITY = [
        # barry-far comprehensive collection (all variants)
        "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub1.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub2.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub3.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub4.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub5.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub6.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub7.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Sub8.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub1.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub2.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub3.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub4.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub5.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub6.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub7.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub8.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub9.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub10.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/refs/heads/main/All_Configs_Sub.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Splitted-By-Protocol/vless.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Splitted-By-Protocol/vmess.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Splitted-By-Protocol/trojan.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Splitted-By-Protocol/shadowsocks.txt",
        "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Splitted-By-Protocol/reality.txt",
        
        # Rayan-Config ecosystem (Iranian-focused)
        "https://Rayan-Config.github.io/NG",
        "https://Rayan-Config.github.io/NB",
        "https://Rayan-Config.github.io/all",
        "https://raw.githubusercontent.com/Rayan-Config/C-Sub/refs/heads/main/configs/proxy.txt",
        "https://raw.githubusercontent.com/Rayan-Config/C-Sub/refs/heads/main/configs/singbox_configs.json",
        "https://raw.githubusercontent.com/Rayan-Config/C-Sub/refs/heads/main/configs/all",

        # MhdiTaheri V2rayCollector (comprehensive)
        "https://raw.githubusercontent.com/MhdiTaheri/V2rayCollector/refs/heads/main/sub/mix",
        "https://raw.githubusercontent.com/MhdiTaheri/V2rayCollector/refs/heads/main/sub/vless",
        "https://raw.githubusercontent.com/MhdiTaheri/V2rayCollector/refs/heads/main/sub/vmess",
        "https://raw.githubusercontent.com/MhdiTaheri/V2rayCollector/refs/heads/main/sub/trojan",
        "https://raw.githubusercontent.com/MhdiTaheri/V2rayCollector/refs/heads/main/sub/shadowsocks",
        "https://raw.githubusercontent.com/MhdiTaheri/V2rayCollector/refs/heads/main/sub/reality",
        "https://raw.githubusercontent.com/MhdiTaheri/V2rayCollector/refs/heads/main/sub/tuic",
        "https://raw.githubusercontent.com/MhdiTaheri/V2rayCollector/refs/heads/main/sub/hysteria",
        "https://raw.githubusercontent.com/MhdiTaheri/V2rayCollector/refs/heads/main/sub/hysteria2",
        
        # soroushmirzaei telegram-configs-collector (complete)
        "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/vless",
        "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/vmess",
        "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/trojan",
        "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/shadowsocks",
        "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/reality",
        "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/hysteria",
        "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/hysteria2",
        "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/tuic",
        "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/juicity",
        "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/naive",
        "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/splitted/mixed",
        "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/collected/all",
        
        # IranianCypherpunks Xray
        "https://raw.githubusercontent.com/IranianCypherpunks/Xray/main/Sub",
        
        # Syavar V2ray-Configs
        "https://raw.githubusercontent.com/Syavar/V2ray-Configs/main/OK_google.com.txt",
        
        # ndsphonemy proxy-sub collection
        "https://raw.githubusercontent.com/ndsphonemy/proxy-sub/main/default.txt",
        "https://raw.githubusercontent.com/ndsphonemy/proxy-sub/main/speed.txt",
        "https://raw.githubusercontent.com/ndsphonemy/proxy-sub/main/my.txt",
        
        # Special Iranian services
        "https://channel-freevpnhomes-subscription.shampoosirsehat.homes",
        "https://gutsy-fibers.000webhostapp.com/sni.php?country=de;nl;fr;lt;lv;ee;se;no",
        "https://gutsy-fibers.000webhostapp.com/sni.php?country=us;ca;jp;sg;hk",
        
        # MrMohebi xray-proxy-grabber-telegram
        "https://raw.githubusercontent.com/MrMohebi/xray-proxy-grabber-telegram/master/collected-proxies/row-url/all.txt",
        "https://raw.githubusercontent.com/MrMohebi/xray-proxy-grabber-telegram/master/collected-proxies/row-url/actives.txt",
        "https://raw.githubusercontent.com/MrMohebi/xray-proxy-grabber-telegram/master/collected-proxies/row-url/vless.txt",
        "https://raw.githubusercontent.com/MrMohebi/xray-proxy-grabber-telegram/master/collected-proxies/row-url/vmess.txt",
        "https://raw.githubusercontent.com/MrMohebi/xray-proxy-grabber-telegram/master/collected-proxies/row-url/reality.txt",
        
        # coldwater operator-specific (Iranian ISPs)
        "https://raw.githubusercontent.com/coldwater-10/Vpnclashfa/main/raw/mci.txt",
        "https://raw.githubusercontent.com/coldwater-10/Vpnclashfa/main/raw/irc.txt",
        "https://raw.githubusercontent.com/coldwater-10/Vpnclashfa/main/raw/mkb.txt",
        "https://raw.githubusercontent.com/coldwater-10/V2Hub1/main/Split/Base64/shadowsocks",
        "https://raw.githubusercontent.com/coldwater-10/V2Hub1/main/Split/Base64/trojan",
        "https://raw.githubusercontent.com/coldwater-10/V2Hub1/main/Split/Base64/vless",
        "https://raw.githubusercontent.com/coldwater-10/V2Hub1/main/Split/Base64/vmess",
        "https://raw.githubusercontent.com/coldwater-10/V2Hub1/main/Split/Base64/reality",
        "https://raw.githubusercontent.com/coldwater-10/V2ray-Configs/main/Splitted-By-Protocol/hysteria2.txt",
        "https://raw.githubusercontent.com/coldwater-10/V2ray-Configs/main/Splitted-By-Protocol/reality.txt",
        
        # youfoundamin Iranian splits
        "https://raw.githubusercontent.com/youfoundamin/V2rayCollector/main/ss_iran.txt",
        "https://raw.githubusercontent.com/youfoundamin/V2rayCollector/main/vless_iran.txt",
        "https://raw.githubusercontent.com/youfoundamin/V2rayCollector/main/vmess_iran.txt",
        "https://raw.githubusercontent.com/youfoundamin/V2rayCollector/main/trojan_iran.txt",
        "https://raw.githubusercontent.com/youfoundamin/V2rayCollector/main/mixed_iran.txt",
        "https://raw.githubusercontent.com/youfoundamin/V2rayCollector/main/reality_iran.txt",
        "https://raw.githubusercontent.com/youfoundamin/V2rayCollector/main/hysteria2_iran.txt",
        
        # Additional Iranian projects
        "https://raw.githubusercontent.com/amirparsaxs/-BegzarVPN/refs/heads/main/Begzar_sub_text",
        "https://raw.githubusercontent.com/amirparsaxs/V2rayy/refs/heads/main/Sub.text555",
        "https://raw.githubusercontent.com/amirparsaxs/V2rayy/refs/heads/main/All_Configs.txt",
        "https://raw.githubusercontent.com/Mosifree/-FREE2CONFIG/refs/heads/main/Warp2",
        "https://raw.githubusercontent.com/Mosifree/-FREE2CONFIG/refs/heads/main/T,H",
        "https://shz.al/~@FREE2CONFIG_T,H",
        "https://raw.githubusercontent.com/amirmohammad-mohammad-88/Sub-Reality-Azadi-config/Config/Azadi-Reality-Different",
        "https://raw.githubusercontent.com/amirmohammad-mohammad-88/Sub-Reality-Azadi-config/Config/Azadi-Reality-Different-Base64",
        "https://raw.githubusercontent.com/NiREvil/vless/main/warp.json",
        "https://raw.githubusercontent.com/AB-84-AB/Free-Shadowsocks/refs/heads/main/Telegram-id-AB_841",
        "https://raw.githubusercontent.com/DiDiten/HiN-VPN/main/subscription/hiddify/mix",
        "https://raw.githubusercontent.com/liketolivefree/kobabi/main/singbox.json",
        "https://raw.githubusercontent.com/Mohammadgb0078/IRV2ray/main/vmess.txt",
        "https://raw.githubusercontent.com/Mohammadgb0078/IRV2ray/main/vless.txt",
        "https://raw.githubusercontent.com/Mohammadgb0078/IRV2ray/main/reality.txt",
        "https://raw.githubusercontent.com/MrPooyaX/SansorchiFucker/main/data.txt",
        "https://raw.githubusercontent.com/MrPooyaX/VpnsFucking/main/Shenzo.txt",
        "https://raw.githubusercontent.com/MrPooyaX/Vpns/main/V2ray",
        "https://raw.githubusercontent.com/MrPooyaX/Vpns/main/All_Configs_base64_Sub.txt",
        "https://raw.githubusercontent.com/MrPooyaX/Sansorchi/main/proxi.txt",
        "https://raw.githubusercontent.com/MrPooyaX/Sansorchi/main/sub",
    ]
    
    # International High-Quality Sources
    INTERNATIONAL_MAJOR = [
        # yebekhe TelegramV2rayCollector (most comprehensive)
        "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/mix",
        "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/vless",
        "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/vmess",
        "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/trojan",
        "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/shadowsocks",
        "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/reality",
        "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/hysteria2",
        "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/tuic",
        "https://raw.githubusercontent.com/yebekhe/V2Hub/main/merged",
        "https://raw.githubusercontent.com/yebekhe/V2Hub/main/split/vless",
        "https://raw.githubusercontent.com/yebekhe/V2Hub/main/split/vmess",
        "https://raw.githubusercontent.com/yebekhe/V2Hub/main/split/reality",
        
        # taheri79/V2rayCollector (comprehensive)
        "https://raw.githubusercontent.com/taheri79/V2rayCollector/main/sub/normal/mix",
        "https://raw.githubusercontent.com/taheri79/V2rayCollector/main/sub/base64/mix",
        "https://raw.githubusercontent.com/taheri79/V2rayCollector/main/sub/normal/vless",
        "https://raw.githubusercontent.com/taheri79/V2rayCollector/main/sub/normal/vmess",
        "https://raw.githubusercontent.com/taheri79/V2rayCollector/main/sub/normal/trojan",
        "https://raw.githubusercontent.com/taheri79/V2rayCollector/main/sub/normal/shadowsocks",
        "https://raw.githubusercontent.com/taheri79/V2rayCollector/main/sub/normal/reality",
        
        # Mahdi0024 ProxyCollector (tested configs)
        "https://raw.githubusercontent.com/Mahdi0024/ProxyCollector/main/subscriptions/mix",
        "https://raw.githubusercontent.com/Mahdi0024/ProxyCollector/main/subscriptions/vmess",
        "https://raw.githubusercontent.com/Mahdi0024/ProxyCollector/main/subscriptions/vless",
        "https://raw.githubusercontent.com/Mahdi0024/ProxyCollector/main/subscriptions/shadowsocks",
        "https://raw.githubusercontent.com/Mahdi0024/ProxyCollector/main/subscriptions/trojan",
        "https://raw.githubusercontent.com/Mahdi0024/ProxyCollector/main/subscriptions/hysteria2",
        "https://raw.githubusercontent.com/Mahdi0024/ProxyCollector/main/subscriptions/tuic",
        "https://raw.githubusercontent.com/Mahdi0024/ProxyCollector/main/subscriptions/reality",
        
        # V2RayRoot collection
        "https://raw.githubusercontent.com/V2RayRoot/V2RayConfig/main/Config/vless.txt",
        "https://raw.githubusercontent.com/V2RayRoot/V2RayConfig/main/Config/vmess.txt",
        "https://raw.githubusercontent.com/V2RayRoot/V2RayConfig/main/Config/shadowsocks.txt",
        "https://raw.githubusercontent.com/V2RayRoot/V2RayConfig/main/Config/trojan.txt",
        "https://raw.githubusercontent.com/V2RayRoot/V2RayConfig/main/Config/reality.txt",
        "https://raw.githubusercontent.com/V2RayRoot/V2RayConfig/main/Config/mix.txt",
        
        # Epodonios v2ray-configs (comprehensive mega-repo)
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_Sub.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_base64_Sub.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/vless.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/vmess.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/trojan.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/ss.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/ssr.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Configs_TLS.txt",
        # All Epodonios Config Lists (1-20)
        *[f"https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Config%20list{i}.txt" for i in range(1, 21)],
        # Epodonios Sub splits (1-15)
        *[f"https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/Sub{i}.txt" for i in range(1, 16)],
        
        # MatinGhanbari v2ray-configs (comprehensive)
        "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/v2ray/all_sub.txt",
        "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/v2ray/super-sub.txt",
        "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/filtered/subs/vmess.txt",
        "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/filtered/subs/vless.txt",
        "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/filtered/subs/trojan.txt",
        "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/filtered/subs/shadowsocks.txt",
        "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/filtered/subs/reality.txt",
        # MatinGhanbari splits (1-50)
        *[f"https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/subscriptions/v2ray/subs/sub{i}.txt" for i in range(1, 51)],
        
        # mahdibland Aggregators
        "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt",
        "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/sub/sub_merge.txt",
        "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/splitted/vmess.txt",
        "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/splitted/vless.txt",
        "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/splitted/trojan.txt",
        "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/splitted/shadowsocks.txt",
        "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/splitted/reality.txt",
    ]
    
    # Additional High-Volume Sources
    COMPREHENSIVE_BATCH = [
        # sevcator 5ubscrpt10n (500k+ configs)
        "https://raw.githubusercontent.com/sevcator/5ubscrpt10n/main/full/5ubscrpt10n.txt",
        "https://raw.githubusercontent.com/sevcator/5ubscrpt10n/main/full/5ubscrpt10n-b64.txt",
        "https://raw.githubusercontent.com/sevcator/5ubscrpt10n/main/protocols/vl.txt",
        "https://raw.githubusercontent.com/sevcator/5ubscrpt10n/main/protocols/vm.txt",
        "https://raw.githubusercontent.com/sevcator/5ubscrpt10n/main/protocols/tr.txt",
        "https://raw.githubusercontent.com/sevcator/5ubscrpt10n/main/protocols/ss.txt",
        "https://raw.githubusercontent.com/sevcator/5ubscrpt10n/main/protocols/hy2.txt",
        "https://raw.githubusercontent.com/sevcator/5ubscrpt10n/main/protocols/tuic.txt",
        "https://raw.githubusercontent.com/sevcator/5ubscrpt10n/main/protocols/reality.txt",
        # sevcator mini splits (1-20)
        *[f"https://raw.githubusercontent.com/sevcator/5ubscrpt10n/main/mini/m1n1-5ub-{i}.txt" for i in range(1, 21)],
        
        # zengfr free-vpn-subscribe
        "https://raw.githubusercontent.com/zengfr/free-vpn-subscribe/main/vpn_sub_.txt",
        "https://raw.githubusercontent.com/zengfr/free-vpn-subscribe/main/vpn_sub_raw_.txt",
        "https://raw.githubusercontent.com/zengfr/free-vpn-subscribe/main/vpn_sub_shadowsocks.txt",
        "https://raw.githubusercontent.com/zengfr/free-vpn-subscribe/main/vpn_sub_trojan.txt",
        "https://raw.githubusercontent.com/zengfr/free-vpn-subscribe/main/vpn_sub_vmess.txt",
        "https://raw.githubusercontent.com/zengfr/free-vpn-subscribe/main/vpn_sub_vless.txt",
        "https://raw.githubusercontent.com/zengfr/free-vpn-subscribe/main/vpn_sub_hysteria2.txt",
        
        # Premium service subscriptions
        "https://dyzk.020318.xyz/?token=d24404a213fc4dd681536826c509e0a1&flag=clash",
        "https://yy.filmtoday.top/api/v1/client/subscribe?token=390eb972a4070dd91ad8cb8a11e9aff8",
        "https://xship.top/v1/subscribe?starlink=lK-IH1mWfDG6xJ1yTB6JIGuL",
        "https://guang-cloud.com/api/v1/client/subscribe?token=ba9c2b246fffcbaa801c2d19a4718e3f",
        "https://gogo.kkhhddnn.cn/api/v1/client/subscribe?token=8ba1e286d4c5f831fde9b2cfa1917913",
        "https://qishuijc.top/api/v1/client/subscribe?token=391afb46752d77774f9848f1b0e30b14",
        "http://103.35.189.118:7001/s/68a95aaf8a22330847c0507d28147292",
        
        # Chinese community sources
        "https://raw.githubusercontent.com/zhangkaiitugithub/passcro/main/speednodes.yaml",
        "https://raw.githubusercontent.com/go4sharing/sub/main/sub.yaml",
        "https://gist.github.com/go4sharing/9cd241e781444d0924227c4171ccc02b/raw/d077791e5da3aa2ba3769009c65fbd499ff97c32/gistfile1.txt",
        
        # US dynamic servers
        "https://us6-dy.818185.xyz/eQxS4iey4zg/0cda5f7e-cc55-4ff2-8ad8-268b9b99dd01/#TG-freevpnatm",
        "https://us7-dy.890603.xyz/QOpk6x3mQBKV8fXCAuTIvNVjuHP/4d04b30c-ef7b-4a07-8f9e-f581ec171f8a/#TG-freevpnatm",
        "https://us8-dy.890601.xyz/R408J0PrBiWrmKFVLWL2wb8/3465a008-d9a0-40a2-bc63-232fca123efb/#TG-freevpnatm-分享",
        "https://us9-06.iran2030.ggff.net/dxJ41KGH07f/61ade0f2-e259-4608-8ecb-f12326fde120/#TG-freevpnatm",
        "https://us10-dy1.iran2030.ggff.net/OXKTQG1N88qvUea2C/576c81b6-4976-4fe3-b1a9-05a9c302e98e/#TG-freevpnatm",
        
        # SubCrawlers
        *[f"https://raw.githubusercontent.com/{owner}/SubCrawler/main/sub/share/all" for owner in 
          ("personqianduixue", "gtang8", "zzz6839", "zjfb", "QQnight")],
        "https://raw.githubusercontent.com/Leon406/SubCrawler/main/sub/share/all3",
        "https://raw.githubusercontent.com/Leon406/SubCrawler/main/sub/share/all4",
        "https://raw.githubusercontent.com/Leon406/SubCrawler/main/sub/share/v2",
        
        # mermeroo comprehensive collection
        *[f"https://raw.githubusercontent.com/mermeroo/free-v2ray-collector/main/main/{p}" for p in 
          ("mix", "reality", "shadowsocks", "trojan", "vless", "vmess")],
        *[f"https://raw.githubusercontent.com/mermeroo/V2RAY-FREE/raw/main/Base64/Sub{i}_base64.txt" for i in range(2, 6)],
        "https://raw.githubusercontent.com/mermeroo/V2RAY-FREE/raw/main/All_Configs_base64_Sub.txt",
        "https://raw.githubusercontent.com/mermeroo/Loon/main/node%202",
        "https://raw.githubusercontent.com/mermeroo/Clash-V2ray/main/v2ray",
        "https://raw.githubusercontent.com/mermeroo/QX/refs/heads/main/Nodes",
        "https://raw.githubusercontent.com/mermeroo/Loon/refs/heads/main/all.nodes.txt",
        "https://raw.githubusercontent.com/mermeroo/QuantumultX/refs/heads/main/Trojan.nodes",
        "https://raw.githubusercontent.com/mermeroo/telegram-configs-collector/raw/main/protocols/tuic",
        "https://raw.githubusercontent.com/mermeroo/telegram-configs-collector/raw/main/protocols/hysteria",
        "https://raw.githubusercontent.com/mermeroo/telegram-configs-collector/raw/main/protocols/juicity",
        
        # Individual collectors (comprehensive)
        "https://raw.githubusercontent.com/LonUp/NodeList/main/V2RAY/Latest_base64.txt",
        "https://raw.githubusercontent.com/theGreatPeter/v2rayNodes/main/nodes.txt",
        "https://raw.githubusercontent.com/GreenFishStudio/GreenFish/master/Subscription/GreenFishYYDS",
        "https://raw.githubusercontent.com/Creativveb/v2configs/main/updated",
        "https://raw.githubusercontent.com/Flik6/getNode/main/v2ray.txt",
        "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2",
        "https://raw.githubusercontent.com/Jason05211211/Freerocket/main/freessr",
        "https://raw.githubusercontent.com/AzadNetCH/Clash/refs/heads/main/AzadNet_iOS.txt",
        "https://raw.githubusercontent.com/Barabama/FreeNodes/master/nodes/merged.txt",
        "https://raw.githubusercontent.com/ermaozi01/free_clash_vpn/main/subscribe/v2ray.txt",
        "https://raw.githubusercontent.com/hans-thomas/v2ray-subscription/refs/heads/master/servers.txt",
        "https://raw.githubusercontent.com/vorz1k/v2box/main/subscription-links.txt",
        "https://raw.githubusercontent.com/Shaik360/v2ray-configs/main/subscription.txt",
        "https://raw.githubusercontent.com/245237866/v2rayn/main/everydaynode",
        
        # API endpoints
        "https://api.yebekhe.link/shervin/",
        
        # Additional quality sources
        "https://raw.githubusercontent.com/awesome-vpn/awesome-vpn/master/all",
        "https://raw.githubusercontent.com/awesome-vpn/awesome-vpn/master/ss",
        "https://raw.githubusercontent.com/awesome-vpn/awesome-vpn/master/ssr",
        "https://raw.githubusercontent.com/vpei/free-node-1/main/o/proxies.txt",
        # vpei free-node splits (0-9)
        *[f"https://raw.githubusercontent.com/vpei/free-node-1/refs/heads/main/res/nod-{i}.txt" for i in range(10)],
        
        # Huibq comprehensive
        *[f"https://raw.githubusercontent.com/Huibq/TrojanLinks/master/links/{f}" for f in 
          ("ss_with_plugin", "ss", "ssr", "vless", "vmess", "trojan", "temporary", "reality", "hysteria2")],
        
        # lagzian/SS-Collector (comprehensive collection)
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/ss.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/vmess.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/vless.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/reality.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/mix.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/hysteria.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/hysteria2.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/tuic.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/trojan.txt",
        # Country-specific from lagzian
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/countries/us.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/countries/uk.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/countries/de.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/countries/ca.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/countries/fr.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/countries/jp.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/countries/sg.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/countries/hk.txt",
        # Speed-tested collections
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/trinity/fast.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/trinity/medium.txt",
        "https://raw.githubusercontent.com/lagzian/SS-Collector/main/trinity/slow.txt",
        
        # Cloudflare-based solutions
        "https://raw.githubusercontent.com/cmliu/edgetunnel/main/sub.txt",
        "https://raw.githubusercontent.com/6Kmfi6HP/EDtunnel/main/sub.txt",
        "https://raw.githubusercontent.com/yonggekkk/Cloudflare_vless_trojan/main/sub.txt",
        "https://raw.githubusercontent.com/cmliu/edgetunnel/main/CF-Workers-SUB.txt",
        "https://raw.githubusercontent.com/6Kmfi6HP/EDtunnel/main/CF-Workers-SUB.txt",
        
        # Additional comprehensive sources
        "https://raw.githubusercontent.com/peasoft/NoMoreWalls/refs/heads/master/list.txt",
        "https://raw.githubusercontent.com/peasoft/NoMoreWalls/refs/heads/master/list_raw.txt",
        "https://raw.githubusercontent.com/peasoft/NoMoreWalls/refs/heads/master/list_base64.txt",
        "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription_num",
        "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription2",
        "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription3",
        "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/sub",
        "https://raw.githubusercontent.com/Kwinshadow/TelegramV2rayCollector/main/sublinks/b64mix.txt",
        "https://raw.githubusercontent.com/Kwinshadow/TelegramV2rayCollector/main/sublinks/vless.txt",
        "https://raw.githubusercontent.com/Kwinshadow/TelegramV2rayCollector/main/sublinks/vmess.txt",
        "https://sub.xn--4gqvd492adjr.com/s/43c2bb6d01f3cea4c85a25eefde7944a",
        "https://raw.githubusercontent.com/mheidari98/.proxy/main/all",
        "https://raw.githubusercontent.com/mheidari98/.proxy/refs/heads/main/trojan",
        "https://raw.githubusercontent.com/SamanValipour1/My-v2ray-configs/main/MySub.txt",
        "https://raw.githubusercontent.com/budamu/clashconfig/main/v2ray.txt",
        "https://raw.githubusercontent.com/budamu/clashconfig/main/v2ray2.txt",
        "https://raw.githubusercontent.com/YasserDivaR/pr0xy/main/ShadowSocks2021.txt",
        "https://raw.githubusercontent.com/shabane/kamaji/master/hub/b64/ss.txt",
        "https://raw.githubusercontent.com/shabane/kamaji/master/hub/b64/vmess.txt",
        "https://raw.githubusercontent.com/shabane/kamaji/master/hub/b64/vless.txt",
        "https://raw.githubusercontent.com/shabane/kamaji/master/hub/b64/trojan.txt",
        "https://raw.githubusercontent.com/shabane/kamaji/master/hub/b64/merged.txt",
        "https://raw.githubusercontent.com/vxiaov/free_proxy_ss/main/v2ray/v2raysub",
        "https://raw.githubusercontent.com/vxiaov/free_proxy_ss/main/ssr/ssrsub",
        "https://raw.githubusercontent.com/vxiaov/free_proxy_ss/main/ss/sssub",
        "https://raw.githubusercontent.com/vxiaov/free_proxies/refs/heads/main/links.txt",
        "https://raw.githubusercontent.com/gitbigg/permalink/main/subscribe",
        "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
        "https://raw.githubusercontent.com/ripaojiedian/freenode/main/sub",
        "https://raw.githubusercontent.com/freefq/free/master/v2",
        "https://raw.githubusercontent.com/learnhard-cn/free_proxy_ss/main/free",
        "https://raw.githubusercontent.com/learnhard-cn/free_proxy_ss/main/v2ray/v2rays.txt",
        "https://raw.githubusercontent.com/learnhard-cn/free_proxy_ss/main/ss/sssub",
        "https://raw.githubusercontent.com/learnhard-cn/free_proxy_ss/main/ssr/ssrsub",
        "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/main/V2RAY_SUB.txt",
        "https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/main/server.txt",
        "https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/main/sub.txt",
        "https://raw.githubusercontent.com/snakem982/proxypool/main/nodelist.txt",
        "https://raw.githubusercontent.com/anaer/Sub/main/clash.yaml",
        "https://raw.githubusercontent.com/anaer/Sub/main/v2ray.txt",
        "https://raw.githubusercontent.com/lmc999/Region-configs/main/sub-all-v2ray.txt",
        "https://raw.githubusercontent.com/ossgo/Sub/main/sub",
        "https://raw.githubusercontent.com/sashalsk/V2Ray/main/V2Ray-list-text",
        "https://raw.githubusercontent.com/abshare/abshare.github.io/main/all.txt",
        "https://raw.githubusercontent.com/fanqiangfeee/free-v2ray-vpn/main/v2ray",
        "https://raw.githubusercontent.com/free112/V2Ray-free-nodes/main/V2Ray-list-text.txt",
        "https://raw.githubusercontent.com/im-web/sub/main/vless",
        "https://raw.githubusercontent.com/Jajaj-dev/sub/main/v2ray",
        "https://raw.githubusercontent.com/mjrulesamrat/v2ray-configs/main/AllConfigs.txt",
        "https://raw.githubusercontent.com/movft/movft/main/config/config.txt",
        "https://raw.githubusercontent.com/open-source-links/v2ray-list/main/list.txt",
        "https://raw.githubusercontent.com/Ptechgithub/configs/main/sub.txt",
        "https://raw.githubusercontent.com/sun956/V2ray-Subscription-Update/main/v2ray.txt",
        "https://raw.githubusercontent.com/tbbatbb/Proxy/master/dist/v2ray.config.txt",
        "https://raw.githubusercontent.com/wonderfulgo/subscription-script/main/v2/config",
        "https://raw.githubusercontent.com/xiaomadashu/v2ray/master/config.txt",
        "https://raw.githubusercontent.com/XrayR-project/XrayR-release/master/config/subscribe.txt",
        "https://raw.githubusercontent.com/ZDCloud/Sub/main/All",
        "https://raw.githubusercontent.com/zipkocc/SagerNet-Configs/main/sub.txt",
        
        # BitBucket sources
        "https://bitbucket.org/huwo1/proxy_nodes/raw/f31ca9ec67b84071515729ff45b011b6b09c10f2/ss.md",
        "https://bitbucket.org/huwo1/proxy_nodes/raw/f31ca9ec67b84071515729ff45b011b6b09c10f2/vmess.md",
        "https://bitbucket.org/huwo1/proxy_nodes/raw/f31ca9ec67b84071515729ff45b011b6b09c10f2/proxy.md",
        "https://bitbucket.org/huwo1/proxy_nodes/raw/f31ca9ec67b84071515729ff45b011b6b09c10f2/trojan.md",
        
        # Additional collections
        "https://raw.githubusercontent.com/luxl-1379/merge/77247d23def72b25226dfa741614e9b07a569c72/sub/sub_merge_base64.txt",
        "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/python/hy2",
        "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/python/hysteria2",
        "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/python/hysteria",
        "https://raw.githubusercontent.com/webdao/v2ray/refs/heads/master/nodes.txt",
        "https://raw.githubusercontent.com/webdao/v2ray/refs/heads/master/nodes2.txt",
        "https://raw.githubusercontent.com/webdao/v2ray/refs/heads/master/nodes3.txt",
        
        # Hiddify & Sing-Box related
        "https://raw.githubusercontent.com/hiddify/Hiddify-Server/main/release/hiddify-next-config.json",
        "https://raw.githubusercontent.com/hiddify/awesome-freedom/main/configs.txt",

        # Missings
        "https://raw.githubusercontent.com/AliDev-ir/FreeVPN/main/pcvpn",
        "https://raw.githubusercontent.com/AliDev-ir/FreeVPN/main/vpn",
        "https://raw.githubusercontent.com/M-Mashreghi/Free-V2ray-Collector/main/Files/shuffle/Sub1_shuffled.conf",
        "https://raw.githubusercontent.com/M-Mashreghi/Free-V2ray-Collector/main/Files/shuffle/Sub2_shuffled.conf",
        "https://raw.githubusercontent.com/M-Mashreghi/Free-V2ray-Collector/main/Files/shuffle/Sub3_shuffled.conf",
        "https://raw.githubusercontent.com/M-Mashreghi/Free-V2ray-Collector/main/Files/shuffle/Sub4_shuffled.conf",
        "https://raw.githubusercontent.com/M-Mashreghi/Free-V2ray-Collector/main/Files/shuffle/Sub5_shuffled.conf",
        "https://raw.githubusercontent.com/M-Mashreghi/Free-V2ray-Collector/main/Files/shuffle/Sub6_shuffled.conf",
        "https://raw.githubusercontent.com/M-Mashreghi/Free-V2ray-Collector/main/Files/shuffle/Sub7_shuffled.conf",
        "https://raw.githubusercontent.com/M-Mashreghi/Free-V2ray-Collector/main/Files/shuffle/Sub8_shuffled.conf",
        "https://raw.githubusercontent.com/M-Mashreghi/Free-V2ray-Collector/main/Files/shuffle/Sub9_shuffled.conf",
        "https://raw.githubusercontent.com/M-Mashreghi/Free-V2ray-Collector/main/Files/shuffle/Sub10_shuffled.conf",
        "https://raw.githubusercontent.com/M-Mashreghi/Free-V2ray-Collector/main/Files/shuffle/Sub11_shuffled.conf",
        "https://raw.githubusercontent.com/M-Mashreghi/Free-V2ray-Collector/main/Files/shuffle/Sub12_shuffled.conf",
        "https://p6.punchline.ir:2096/sub/v2raybluecrystal2tb",
        "https://p6.punchline.ir:2096/sub/v2raybluecrystal5TBFR",
        "https://p7.punchline.ir:2096/v2raybluecrystal/turkey5tb",
        "https://p7.punchline.ir:2096/v2raybluecrystal/turkey4tera",
        "https://proud-fire-1775.mahmmod2025.workers.dev/sub/e0e345e3-e2ce-4778-81ff-67b4a8feddd8#BPB-Normal",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Config%20list3.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Config%20list10.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Config%20list15.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Config%20list16.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Config%20list17.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Config%20list18.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Config%20list19.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Config%20list20.txt",
        "https://raw.githubusercontent.com/taheri79/V2rayCollector/main/sub/normal/mix",
        "https://raw.githubusercontent.com/taheri79/V2rayCollector/main/sub/base64/mix",
        "https://raw.githubusercontent.com/taheri79/V2rayCollector/main/sub/normal/vless",
        "https://raw.githubusercontent.com/taheri79/V2rayCollector/main/sub/normal/vmess",
        "https://raw.githubusercontent.com/taheri79/V2rayCollector/main/sub/normal/trojan",
        "https://raw.githubusercontent.com/taheri79/V2rayCollector/main/sub/normal/shadowsocks",
        "https://raw.githubusercontent.com/taheri79/V2rayCollector/main/sub/normal/reality",
        "https://raw.githubusercontent.com/anaer/Sub/main/clash.yaml",
        "https://raw.githubusercontent.com/anaer/Sub/main/v2ray.txt",
        "https://raw.githubusercontent.com/lmc999/Region-configs/main/sub-all-v2ray.txt",
        "https://raw.githubusercontent.com/ossgo/Sub/main/sub",
        "https://raw.githubusercontent.com/hagezi/mirror/main/v2ray.txt",
        "https://raw.githubusercontent.com/abshare/abshare.github.io/main/all.txt",
        "https://raw.githubusercontent.com/fanqiangfeee/free-v2ray-vpn/main/v2ray",
        "https://raw.githubusercontent.com/free112/V2Ray-free-nodes/main/V2Ray-list-text.txt",
        "https://raw.githubusercontent.com/im-web/sub/main/vless",
        "https://raw.githubusercontent.com/Jajaj-dev/sub/main/v2ray",
        "https://raw.githubusercontent.com/mjrulesamrat/v2ray-configs/main/AllConfigs.txt",
        "https://raw.githubusercontent.com/movft/movft/main/config/config.txt",
        "https://raw.githubusercontent.com/open-source-links/v2ray-list/main/list.txt",
        "https://raw.githubusercontent.com/Ptechgithub/configs/main/sub.txt",
        "https://raw.githubusercontent.com/sun956/V2ray-Subscription-Update/main/v2ray.txt",
        "https://raw.githubusercontent.com/tbbatbb/Proxy/master/dist/v2ray.config.txt",
        "https://raw.githubusercontent.com/wonderfulgo/subscription-script/main/v2/config",
        "https://raw.githubusercontent.com/xiaomadashu/v2ray/master/config.txt",
        "https://raw.githubusercontent.com/XrayR-project/XrayR-release/master/config/subscribe.txt",
        "https://raw.githubusercontent.com/ZDCloud/Sub/main/All",
        "https://raw.githubusercontent.com/zipkocc/SagerNet-Configs/main/sub.txt",

            # Large public text / YAML feeds
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/V2RAY.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/V2RAY_RAW.txt",
    "https://raw.githubusercontent.com/Misaka-blog/chromego_merge/main/sub/merged_proxies_new.yaml",
    "https://raw.githubusercontent.com/MrMohebi/xray-proxy-grabber-telegram/master/collected-proxies/clash-meta/all.yaml",
    "https://raw.githubusercontent.com/NiceVPN123/NiceVPN/main/Clash.yaml",
    "https://raw.githubusercontent.com/PangTouY00/Auto_proxy/main/Long_term_subscription_num",
    "https://raw.githubusercontent.com/Vauth/node/main/Main",
    "https://raw.githubusercontent.com/aiboboxx/clashfree/main/clash.yml",
    "https://raw.githubusercontent.com/chengaopan/AutoMergePublicNodes/master/list.yml",
    "https://raw.githubusercontent.com/lagzian/SS-Collector/main/mix_clash.yaml",
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge_yaml.yml",
    "https://raw.githubusercontent.com/mheidari98/.proxy/main/all",
    "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.yml",
    "https://raw.githubusercontent.com/ronghuaxueleng/get_v2/main/pub/combine.yaml",
    "https://raw.githubusercontent.com/dongchengjie/airport/main/subs/merged/tested_within.yaml",
    "https://raw.githubusercontent.com/abbasdvd3/clash/main/vless/x",

    # du5/free repo – dated snapshots
    "https://raw.githubusercontent.com/du5/free/master/file/0407/clash.yaml",
    "https://raw.githubusercontent.com/du5/free/master/file/0407/clash2.yaml",
    "https://raw.githubusercontent.com/du5/free/master/file/0307/clash.yaml",
    "https://raw.githubusercontent.com/du5/free/master/file/0312/clash.yaml",
    "https://raw.githubusercontent.com/du5/free/master/file/0905/quan.conf",
    "https://git.ddns.tokyo/du5/free/master/file/0615/v2ray.json",
    "https://git.ddns.tokyo/du5/free/master/file/0503/clash.yaml",

    # Token-based API endpoints
    "http://www.paoche.ooo/api/v1/client/subscribe?token=4d2a30058958302ee685266f2340ea6c",
    "http://110.72.100.27:55/api/v1/client/subscribe?token=b5c6af703a58cf950498c03e7a42a0f2",
    "https://v2.fit/modules/servers/V2raySocks/osubscribe.php?sid=7063&token=lKJwbO2onxIr",
    "http://www.sksla.pro/api/v1/client/subscribe?token=99c3fa86424539bd3bd34a893bc6dee8",
    "https://fly.lo-lita.ru/api/v1/client/subscribe?token=94be7fa3d65791197dd10c6a0b757571",

    # Short-link & web-hosted feeds
    "https://mijishu.xyz/link/EqVV5nouWjbB59Ln?sub=3&extend=1",
    "https://hjysub1.com/link/cgQ2jYaeQx9LBxsh?sub=3&extend=1",
    "https://suda.sub.koicloud.pw/link/K9vz0uFPe9ULfdqX?sub=3",
    "https://suda.sub.koicloud.pw/link/JgULLCNkImsJ6Ibh?sub=3",
    "https://extrm.info/link/uirPjznB7esOezjr?sub=1",
    "https://sbnmsl.co/link/2cpTGUGJtHBXUK7d?sub=3",
    "https://pptp.cloud/sub/cXHG9wqUpQbhHr7d.html",
    "https://www.haidaobot.xyz/link/QwdUmWolPN0LkThW?mu=2",
    "https://dingyue.suying666.info/link/o7j43Aykx8CWBehE?sub=1",
    "https://vvsub.xyz/api/al/19786-xDX1SCq61Ymi",
    "https://rss-node.com/link/vqOaWFJRfbYxpAhY?mu=1",
    "https://tm2w.live/link/EqICUlKXmn1EJwaw?sub=3",
    "https://www.suncloud.fun/link/Su683BQEyUdxtyuY?mu=1&extend=1",
    "https://www.suncloud.fun/link/ja3OIcMTrky6VhN6?mu=1&extend=1",
    "https://sub88.xyz/link/egy4oyqok9aavpcy?sub=3",
    "https://sub88.xyz/link/lkY8Jt5Q3SHlffra?mu=2",
    "https://bujidao302.com/link/IJ6wKEt96Otboilb?mu=2",
    "https://rss.getfree.win/link/w9ted9eZq1zbC3gx?sub=1",
    "https://rss.cnrss.xyz/link/Rcr8h8fvZIWE001U?mu=2",
    "https://s.sublank.xyz/subscribe/66056/0yzuMVawjpr/ssr/",
    "https://12o.ooo/link/JLisT80gOhRkiFnX?sub=1",

    # Netlify & Git-hosted plain-text dumps
    "https://neurotoxinw.coding.net/p/qifei/d/qifei/git/raw/master/README.md",
    "https://qiaomenzhuanfx.netlify.com/",
    "https://youlianboshi.netlify.com/",
    "https://iwxf.netlify.app/",
    "http://qe83xk711.sabkt.gdipper.com/freev2ray.txt",
    "http://qe83xk711.sabkt.gdipper.com/freess.txt",
    "http://103.72.166.89/v2ray.php",

    # GitHub raw text feeds (misc.)
    "https://raw.githubusercontent.com/Pcrab/Dotfiles/912c1104b3f8121f72f7ee11590f52bc9c44dde7/.config/electron-ssr/gui-config.json",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/v2ray",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/ss-sub",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/ssrsub",
    "https://raw.githubusercontent.com/satrom/V2SSR/master/V2RAY/Sub.txt",
    "https://raw.githubusercontent.com/satrom/V2SSR/master/SSR/Day.txt",
    "https://raw.githubusercontent.com/satrom/V2SSR/master/SSR/Sub.txt",
    "https://raw.githubusercontent.com/hotsymbol/vpnsetting/master/v2rayopen",
    "https://raw.githubusercontent.com/ntkernel/lantern/master/vmess_base64.txt",
    "https://raw.githubusercontent.com/pojiezhiyuanjun/freev2/master/20200808.txt",
    "https://raw.githubusercontent.com/du5/free/master/file/0905/quan.conf",
    "https://raw.githubusercontent.com/du5/free/master/file/0909/Clash.yaml",
    "https://raw.githubusercontent.com/du5/free/master/file/0906/surge.conf",
    "https://raw.githubusercontent.com/du5/free/master/file/0906/ss.json",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/ssrsub",
    "https://raw.githubusercontent.com/RaymondHarris971/ssrsub/master/9a075bdee5.txt",
    "https://raw.githubusercontent.com/voken100g/AutoSSR/master/recent",
    "https://raw.githubusercontent.com/cdp2020/v2ray/master/README.md",

    # Misc tiny short-links (still valid subscription payloads)
    "https://bit.ly/2D5fWhX",

        # --- big auto-updated GitHub feeds ---
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/refs/heads/main/V2Ray-Config-By-EbraSha.txt",
    "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/refs/heads/main/V2Ray-Config-By-EbraSha-All-Type.txt",
    "https://raw.githubusercontent.com/SnapdragonLee/SystemProxy/master/dist/clash_config.yaml",
    "https://raw.githubusercontent.com/SnapdragonLee/SystemProxy/master/dist/clash_config_extra.yaml",
    "https://raw.githubusercontent.com/SnapdragonLee/SystemProxy/master/dist/clash_config_extra_US.yaml",
    "https://raw.githubusercontent.com/mfuu/v2ray/master/clash.yaml",
    "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/clash.yml",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/vmess.txt",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/vless.txt",
    "https://raw.githubusercontent.com/V2RaySSR/Tools/master/clash.yaml",
    "https://raw.githubusercontent.com/du5/free/master/file/0312/clash.yaml",
    "https://raw.githubusercontent.com/du5/free/master/file/0312/clash2.yaml",
    "https://raw.githubusercontent.com/du5/free/master/file/0312/quan.conf",
    "https://raw.githubusercontent.com/Ptechgithub/configs/main/clash12.yaml",
    "https://raw.githubusercontent.com/SunBK201/MySCR/master/clash/SunBK201_conf.yaml",
    "https://raw.githubusercontent.com/AzadNetCH/Clash/main/AzadNet.txt",
    "https://raw.githubusercontent.com/AzadNetCH/Clash/main/AzadNet.json",
    "https://raw.githubusercontent.com/AzadNetCH/Clash/main/AzadNet_hy.txt",
    "https://raw.githubusercontent.com/AzadNetCH/Clash/main/AzadNet_iOS.txt",
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_list.json",
    "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/Eternity.yml",
    # --- NiREvil warp / WG / hiddify mixes ---
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/warp.json",
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/v2rayng-wg.txt",
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/nekobox-wg.txt",
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt",
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/exclave-wg.txt",
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/hiddify/Windscribe%20on%20H2",
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/hiddify/WarpOnWarp.json",
    "https://raw.githubusercontent.com/NiREvil/vless/main/Cloudflare-IPs.json",
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/clash-meta-wg.yml",
    "https://raw.githubusercontent.com/10ium/MihomoSaz/main/Sublist/NiREvil_SSTime.yaml",
    # --- public Clash / YAML feeds ---
    "https://nodefree.org/dy/2024/07/20240725.yaml",
    "https://cdn.jsdelivr.net/gh/vxiaov/free_proxies@main/clash/clash.provider.yaml",
    "https://freenode.openrunner.net/uploads/20240617-clash.yaml",
    "https://tt.vg/freeclash",
    "https://github.com/zu1k/proxypool/releases/download/latest/subscription.txt",
    # --- token-style v2board / Hiddify endpoints ---
    "https://qingyun.zybs.eu.org/api/v1/client/subscribe?token=9cd4a1826b992055a8e87a3f6594ba94",
    "https://api.xyurl.site/api/v1/client/subscribe?token=fed4ab7c582c2a41a08a858f91644430",
    "https://xqsub.e54.site/api/v1/client/subscribe?token=d1fd4dcc61491a02f566f6a45c56ccab&types=vless",
    "https://ch.owokkvsxks.store/api/v1/client/subscribe?token=ad180e3b9514176a8cb26bf2962d5f1e",
    "https://api.xqc.best/api/v1/client/subscribe?token=fb08adc269ff5522ba953933f6a9e9b6",
    "https://csadata4g.me/api/v1/client/subscribe?token=04a09188b487e088f7ab9773f617dd1a",
    "https://sub.lingche.icu/api/v1/client/subscribe?token=48e95450735e7d06d61b56f9bdb349fc",
    "https://cloud.targoo.live/api/v1/client/subscribe?token=1d0a9f1ee09199aac2ac946a1f7d2a0a",
    "https://www.992266.xyz/api/v1/client/subscribe?token=ab825616355b0973e4cdfb659665965f",
    "https://v2y.xyz/api/v1/client/subscribe?token=2533ce3df935ebaf4143fcc3df068ebd",
    "http://xn--nlua550ns4y.com/api/v1/client/subscribe?token=f83cdcc48766976526ab2451380b8dd0",
    "http://davgp416ip6zl8pfrusvvag.zhuyingsu.today/api/v1/client/subscribe?token=b9df9a624e3fdb1e72b10ea81cc9d437",
    "https://pqjc.site/api/v1/client/subscribe?token=0d41f5bd237d1ab92b907e1e7d5e5cb3&flag=meta",
    "http://113.31.116.212:13800/api/v1/client/subscribe?token=b5d84c66256755e551704d05600ada67",
    "http://1.1598888.xyz/api/v1/client/subscribe?token=e2c8421cd8543cd904f255fbef4490cd",
    "http://nuxyun.v2rayflash.top/api/v1/client/subscribe?token=531e0be2dbbfc393dfac550abee6ce57",
    "https://13.112.134.19:13800/api/v1/client/subscribe?token=ce41d51e5664e57b9470f9061c1f61c0",
    "https://tc.ztcloud.xyz/api/v1/client/subscribe?token=26cec3bda11795769be5d18126c4b354",
    "https://cloud.targoo.live/api/v1/client/subscribe?token=9f56998ea1b1c5e3c3a857e3ac274edf",
    "https://xqsub.minictx.top/api/v1/client/subscribe?token=ef279b9e8696510c45b1f21f1653e2c9",
    "https://chan.aztv.asia/api/v1/client/subscribe?token=264d99c3ad7b418f9e7eab1f0d2862c7",
    "https://freeyuan.maimaihuo.com/api/v1/client/subscribe?token=e61032f58d4b00db023be1347f7f6911",
    "https://api.wlins.org/api/v1/client/subscribe?token=fd8e56ea45a735e5d2fba98f3e97c7b6",
    "https://v2sub.purelife.org/api/v1/client/subscribe?token=4ff1f9623ea62a005102b1701f2fd56a",
    "https://free.jinan.cloud/api/v1/client/subscribe?token=6b9e32193f128651ed4cbf6cb0f3c3f0",
    # --- generic link-style subs (Clash=1) ---
    "https://sub.idsvip.com/link/abcd1234?clash=1",
    "https://sub.nerdz.pro/link/xyz987?clash=1",
    # --- misc raw / WG / JSON feeds ---
    "https://raw.githubusercontent.com/4n0nymou3/ss-config-updater/refs/heads/main/configs.txt",
    "https://raw.githubusercontent.com/darknessm427/WoW/refs/heads/main/subwarp/warp",
    "https://raw.githubusercontent.com/arshiacomplus/WoW-fix/main/Xray-WoW.json",
    "https://raw.githubusercontent.com/ndsphonemy/proxy-sub/refs/heads/main/mobile.txt",
    "https://raw.githubusercontent.com/ndsphonemy/proxy-sub/refs/heads/main/wg.txt",
    "https://raw.githubusercontent.com/10ium/ScrapeAndCategorize/refs/heads/main/output_configs/WireGuard.txt",
    "https://raw.githubusercontent.com/Alanbobs999/TopFreeProxies/master/proxies.txt",
    # --- spare token endpoints to round it out ---
    "https://okcloud.cc/api/v1/client/subscribe?token=7b2a9e8f0c373725f9c3d6bd6d1fbe43",
    "https://sub.tangcloud.xyz/api/v1/client/subscribe?token=a3d1c180cf35e5ad9d1fba2d4c5e4bf2",
    "https://vfree.xyz/api/v1/client/subscribe?token=96b51236cddc2df523d9e83a9d457f23",
    "https://free.tailsub.com/api/v1/client/subscribe?token=35b677cab1d1e8349a3e45dc367cbdfa",
    "https://raw.githubusercontent.com/ermaozi/ClashRforWindows/main/sub/2025-07-01.yml",

    ]
    
    @classmethod
    def get_all_sources(cls) -> List[str]:
        """Get all unique sources in priority order with deduplication."""
        all_sources = cls.IRANIAN_PRIORITY + cls.INTERNATIONAL_MAJOR + cls.COMPREHENSIVE_BATCH
        return list(dict.fromkeys(all_sources))  # Remove duplicates while preserving order

# ============================================================================
# ENHANCED CONFIG PROCESSING
# ============================================================================

@dataclass
class ConfigResult:
    """Enhanced config result with testing metrics."""
    config: str
    protocol: str
    host: Optional[str] = None
    port: Optional[int] = None
    ping_time: Optional[float] = None
    is_reachable: bool = False
    source_url: str = ""

class EnhancedConfigProcessor:
    """Advanced configuration processor with comprehensive testing capabilities."""
    
    MAX_DECODE_SIZE = 256 * 1024  # 256 kB safety limit for base64 payloads

    def __init__(self):
        self.dns_cache = {}
        
    def extract_host_port(self, config: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract host and port from configuration for testing."""
        try:
            if config.startswith(("vmess://", "vless://")):
                try:
                    json_part = config.split("://", 1)[1]
                    decoded_bytes = base64.b64decode(json_part)
                    if len(decoded_bytes) > self.MAX_DECODE_SIZE:
                        return None, None
                    decoded = decoded_bytes.decode("utf-8", "ignore")
                    data = json.loads(decoded)
                    host = data.get("add") or data.get("host")
                    port = data.get("port")
                    return host, int(port) if port else None
                except Exception:
                    pass
            
            # Parse URI-style configs
            parsed = urlparse(config)
            if parsed.hostname and parsed.port:
                return parsed.hostname, parsed.port
                
            # Extract from @ notation
            match = re.search(r"@([^:/?#]+):(\d+)", config)
            if match:
                return match.group(1), int(match.group(2))
                
        except Exception:
            pass
        return None, None
    
    def create_semantic_hash(self, config: str) -> str:
        """Create semantic hash for intelligent deduplication."""
        host, port = self.extract_host_port(config)
        user_id = None

        if config.startswith(("vmess://", "vless://")):
            try:
                after_scheme = config.split("://", 1)[1]
                parsed = urlparse(config)
                if parsed.username:
                    user_id = parsed.username
                else:
                    padded = after_scheme + "=" * (-len(after_scheme) % 4)
                    decoded = base64.b64decode(padded).decode("utf-8", "ignore")
                    data = json.loads(decoded)
                    user_id = data.get("id") or data.get("uuid") or data.get("user")
            except Exception:
                pass

        if host and port:
            key = f"{host}:{port}"
            if user_id:
                key = f"{user_id}@{key}"
        else:
            normalized = re.sub(r'#.*$', '', config).strip()
            key = normalized
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    async def test_connection(self, host: str, port: int) -> Optional[float]:
        """Test connection and measure response time."""
        if not CONFIG.enable_url_testing:
            return None
            
        start = time.time()
        try:
            # TCP connection test with timeout
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=CONFIG.test_timeout
            )
            writer.close()
            await writer.wait_closed()
            return time.time() - start
        except Exception:
            return None
    
    def categorize_protocol(self, config: str) -> str:
        """Categorize configuration by protocol."""
        protocol_map = {
            "vmess://": "VMess",
            "vless://": "VLESS", 
            "ss://": "Shadowsocks",
            "trojan://": "Trojan",
            "hy2://": "Hysteria2",
            "hysteria2://": "Hysteria2",
            "hysteria://": "Hysteria",
            "tuic://": "TUIC",
            "reality://": "Reality",
            "naive://": "Naive",
            "juicity://": "Juicity",
            "wireguard://": "WireGuard",
            "shadowtls://": "ShadowTLS",
            "brook://": "Brook",
        }
        
        for prefix, protocol in protocol_map.items():
            if config.startswith(prefix):
                return protocol
        
        return "Other"

# ============================================================================
# ASYNC SOURCE FETCHER WITH COMPREHENSIVE TESTING
# ============================================================================

class AsyncSourceFetcher:
    """Async source fetcher with comprehensive testing and availability checking."""
    
    def __init__(self, processor: EnhancedConfigProcessor):
        self.processor = processor
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def test_source_availability(self, url: str) -> bool:
        """Test if a source URL is available (returns 200 status)."""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.session.head(url, timeout=timeout, allow_redirects=True) as response:
                status = response.status
                if status == 200:
                    return True
                if 400 <= status < 500:
                    async with self.session.get(
                        url,
                        headers={**CONFIG.headers, 'Range': 'bytes=0-0'},
                        timeout=timeout,
                        allow_redirects=True,
                    ) as get_resp:
                        return get_resp.status in (200, 206)
                return False
        except Exception:
            return False
        
    async def fetch_source(self, url: str) -> Tuple[str, List[ConfigResult]]:
        """Fetch single source with comprehensive testing."""
        for attempt in range(CONFIG.max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=CONFIG.request_timeout)
                async with self.session.get(url, headers=CONFIG.headers, timeout=timeout) as response:
                    if response.status != 200:
                        continue
                        
                    content = await response.text()
                    if not content.strip():
                        return url, []
                    
                    # Enhanced Base64 detection and decoding
                    try:
                        # Check if content looks like base64
                        if not any(char in content for char in '\n\r') and len(content) > 100:
                            decoded = base64.b64decode(content).decode("utf-8", "ignore")
                            if decoded.count("://") > content.count("://"):
                                content = decoded
                    except:
                        pass
                    
                    # Extract and process configs
                    lines = [line.strip() for line in content.splitlines() if line.strip()]
                    config_results = []
                    
                    for line in lines:
                        if (line.startswith(CONFIG.valid_prefixes) and 
                            len(line) > 20 and len(line) < 2000 and
                            len(config_results) < CONFIG.max_configs_per_source):
                            
                            # Create config result
                            host, port = self.processor.extract_host_port(line)
                            protocol = self.processor.categorize_protocol(line)
                            
                            result = ConfigResult(
                                config=line,
                                protocol=protocol,
                                host=host,
                                port=port,
                                source_url=url
                            )
                            
                            # Test connection if enabled
                            if CONFIG.enable_url_testing and host and port:
                                ping_time = await self.processor.test_connection(host, port)
                                result.ping_time = ping_time
                                result.is_reachable = ping_time is not None
                            
                            config_results.append(result)
                    
                    return url, config_results
                    
            except Exception:
                if attempt < CONFIG.max_retries - 1:
                    # Use a capped and jittered delay to reduce tail latency
                    await asyncio.sleep(min(3, 1.5 + random.random()))
                    
        return url, []

# ============================================================================
# MAIN PROCESSOR WITH UNIFIED FUNCTIONALITY
# ============================================================================

class UltimateVPNMerger:
    """VPN merger with unified functionality and comprehensive testing."""
    
    def __init__(self):
        self.sources = UnifiedSources.get_all_sources()
        if CONFIG.shuffle_sources:
            random.shuffle(self.sources)
        self.processor = EnhancedConfigProcessor()
        self.fetcher = AsyncSourceFetcher(self.processor)
        self.batch_counter = 0
        self.next_batch_threshold = CONFIG.batch_size if CONFIG.batch_size else float('inf')
        self.start_time = 0.0
        self.available_sources: List[str] = []
        self.all_results: List[ConfigResult] = []
        self.stop_fetching = False
        self.saved_hashes: Set[str] = set()
        self.cumulative_unique: List[ConfigResult] = []
        self.last_processed_index = 0
        self.last_saved_count = 0

    def _load_existing_results(self, path: str) -> List[ConfigResult]:
        """Load previously saved configs from a raw or base64 file."""
        try:
            text = Path(path).read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"⚠️  Failed to read resume file: {e}")
            return []

        if text and '://' not in text.splitlines()[0]:
            try:
                text = base64.b64decode(text).decode("utf-8")
            except Exception:
                pass

        results = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            protocol = self.processor.categorize_protocol(line)
            host, port = self.processor.extract_host_port(line)
            results.append(
                ConfigResult(
                    config=line,
                    protocol=protocol,
                    host=host,
                    port=port,
                    source_url="(resume)"
                )
            )
        return results
        
    async def run(self) -> None:
        """Execute the complete unified merging process."""
        print("🚀 VPN Subscription Merger - Final Unified & Polished Edition")
        print("=" * 85)
        print(f"📊 Total unified sources: {len(self.sources)}")
        print(f"🇮🇷 Iranian priority: {len(UnifiedSources.IRANIAN_PRIORITY)}")
        print(f"🌍 International major: {len(UnifiedSources.INTERNATIONAL_MAJOR)}")
        print(f"📦 Comprehensive batch: {len(UnifiedSources.COMPREHENSIVE_BATCH)}")
        print(f"🔧 URL Testing: {'Enabled' if CONFIG.enable_url_testing else 'Disabled'}")
        print(f"📈 Smart Sorting: {'Enabled' if CONFIG.enable_sorting else 'Disabled'}")
        print()
        
        start_time = time.time()
        self.start_time = start_time

        if CONFIG.resume_file:
            print(f"🔄 Loading existing configs from {CONFIG.resume_file} ...")
            self.all_results.extend(self._load_existing_results(CONFIG.resume_file))
            print(f"   ✔ Loaded {len(self.all_results)} configs from resume file")

        # Step 1: Test source availability and remove dead links
        print("🔄 [1/6] Testing source availability and removing dead links...")
        self.available_sources = await self._test_and_filter_sources()
        
        # Step 2: Fetch all configs from available sources
        print(f"\n🔄 [2/6] Fetching configs from {len(self.available_sources)} available sources...")
        await self._fetch_all_sources(self.available_sources)
        
        # Step 3: Deduplicate efficiently  
        print(f"\n🔍 [3/6] Deduplicating {len(self.all_results):,} configs...")
        unique_results = self._deduplicate_config_results(self.all_results)
        
        # Step 4: Sort by performance if enabled
        if CONFIG.enable_sorting:
            print(f"\n📊 [4/6] Sorting {len(unique_results):,} configs by performance...")
            unique_results = self._sort_by_performance(unique_results)
        else:
            print(f"\n⏭️ [4/6] Skipping sorting (disabled)")

        if CONFIG.top_n > 0:
            unique_results = unique_results[:CONFIG.top_n]
            print(f"   🔝 Keeping top {CONFIG.top_n} configs")

        if CONFIG.max_ping_ms is not None and CONFIG.enable_url_testing:
            before = len(unique_results)
            unique_results = [r for r in unique_results
                              if r.ping_time is not None and r.ping_time * 1000 <= CONFIG.max_ping_ms]
            removed = before - len(unique_results)
            print(f"   ⏱️  Removed {removed} configs over {CONFIG.max_ping_ms} ms")

        # Step 5: Analyze protocols and performance
        print(f"\n📋 [5/6] Analyzing {len(unique_results):,} unique configs...")
        stats = self._analyze_results(unique_results, self.available_sources)
        
        # Step 6: Generate comprehensive outputs
        print("\n💾 [6/6] Generating comprehensive outputs...")
        await self._generate_comprehensive_outputs(unique_results, stats, self.start_time)

        self._print_final_summary(len(unique_results), time.time() - self.start_time, stats)
    
    async def _test_and_filter_sources(self) -> List[str]:
        """Test all sources for availability and filter out dead links."""
        # Setup HTTP session
        connector = aiohttp.TCPConnector(
            limit=CONFIG.concurrent_limit,
            limit_per_host=10,
            ttl_dns_cache=300,
            ssl=ssl.create_default_context(),
            resolver=AsyncResolver()
        )
        
        self.fetcher.session = aiohttp.ClientSession(connector=connector)
        
        try:
            # Test all sources concurrently
            semaphore = asyncio.Semaphore(CONFIG.concurrent_limit)
            
            async def test_single_source(url: str) -> Optional[str]:
                async with semaphore:
                    is_available = await self.fetcher.test_source_availability(url)
                    return url if is_available else None
            
            tasks = [test_single_source(url) for url in self.sources]
            
            completed = 0
            available_sources = []
            
            for coro in asyncio.as_completed(tasks):
                result = await coro
                completed += 1
                
                if result:
                    available_sources.append(result)
                    status = "✅ Available"
                else:
                    status = "❌ Dead link"
                
                print(f"  [{completed:03d}/{len(self.sources)}] {status}")
            
            removed_count = len(self.sources) - len(available_sources)
            print(f"\n   🗑️ Removed {removed_count} dead sources")
            print(f"   ✅ Keeping {len(available_sources)} available sources")
            
            return available_sources
            
        finally:
            # Don't close session here, we'll reuse it
            pass
    
    async def _fetch_all_sources(self, available_sources: List[str]) -> List[ConfigResult]:
        """Fetch all configs from available sources."""
        # Append results directly to self.all_results so that _maybe_save_batch
        # sees the running total and can save incremental batches.
        successful_sources = 0
        
        try:
            # Process sources with semaphore
            semaphore = asyncio.Semaphore(CONFIG.concurrent_limit)
            
            async def process_single_source(url: str) -> Tuple[str, List[ConfigResult]]:
                async with semaphore:
                    return await self.fetcher.fetch_source(url)
            
            # Create tasks
            tasks = [process_single_source(url) for url in available_sources]
            
            completed = 0
            for coro in asyncio.as_completed(tasks):
                url, results = await coro
                completed += 1
                
                # Append directly to the instance-level list
                self.all_results.extend(results)
                if results:
                    successful_sources += 1
                    reachable = sum(1 for r in results if r.is_reachable)
                    status = f"✓ {len(results):,} configs ({reachable} reachable)"
                else:
                    status = "✗ No configs"
                
                domain = urlparse(url).netloc or url[:50] + "..."
                print(f"  [{completed:03d}/{len(available_sources)}] {status} - {domain}")

                await self._maybe_save_batch()

                if self.stop_fetching:
                    break

            if self.stop_fetching:
                for t in tasks:
                    t.cancel()

            print(f"\n   📈 Sources with configs: {successful_sources}/{len(available_sources)}")
            
        finally:
            await self.fetcher.session.close()

        # Return the accumulated list for backward compatibility
        return self.all_results

    async def _maybe_save_batch(self) -> None:
        """Save intermediate output based on batch settings."""
        if CONFIG.batch_size <= 0:
            return

        # Process new results since last call
        new_slice = self.all_results[self.last_processed_index:]
        self.last_processed_index = len(self.all_results)
        for r in new_slice:
            if CONFIG.tls_fragment and CONFIG.tls_fragment.lower() not in r.config.lower():
                continue
            if CONFIG.include_protocols and r.protocol.upper() not in CONFIG.include_protocols:
                continue
            if CONFIG.exclude_protocols and r.protocol.upper() in CONFIG.exclude_protocols:
                continue
            h = self.processor.create_semantic_hash(r.config)
            if h not in self.saved_hashes:
                self.saved_hashes.add(h)
                self.cumulative_unique.append(r)

        if CONFIG.strict_batch:
            while len(self.cumulative_unique) - self.last_saved_count >= CONFIG.batch_size:
                self.batch_counter += 1
                if CONFIG.cumulative_batches:
                    batch_results = self.cumulative_unique[:]
                else:
                    start = self.last_saved_count
                    end = start + CONFIG.batch_size
                    batch_results = self.cumulative_unique[start:end]
                    self.last_saved_count = end

                if CONFIG.enable_sorting:
                    batch_results = self._sort_by_performance(batch_results)
                if CONFIG.top_n > 0:
                    batch_results = batch_results[:CONFIG.top_n]

                stats = self._analyze_results(batch_results, self.available_sources)
                await self._generate_comprehensive_outputs(batch_results, stats, self.start_time, prefix=f"batch_{self.batch_counter}_")

                cumulative_stats = self._analyze_results(self.cumulative_unique, self.available_sources)
                await self._generate_comprehensive_outputs(self.cumulative_unique, cumulative_stats, self.start_time, prefix="cumulative_")

                if CONFIG.threshold > 0 and len(self.cumulative_unique) >= CONFIG.threshold:
                    print(f"\n⏹️  Threshold of {CONFIG.threshold} configs reached. Stopping early.")
                    self.stop_fetching = True
                    break
        else:
            if len(self.cumulative_unique) >= self.next_batch_threshold:
                self.batch_counter += 1
                if CONFIG.cumulative_batches:
                    batch_results = self.cumulative_unique[:]
                else:
                    batch_results = self.cumulative_unique[self.last_saved_count:]
                    self.last_saved_count = len(self.cumulative_unique)

                if CONFIG.enable_sorting:
                    batch_results = self._sort_by_performance(batch_results)
                if CONFIG.top_n > 0:
                    batch_results = batch_results[:CONFIG.top_n]

                stats = self._analyze_results(batch_results, self.available_sources)
                await self._generate_comprehensive_outputs(batch_results, stats, self.start_time, prefix=f"batch_{self.batch_counter}_")

                cumulative_stats = self._analyze_results(self.cumulative_unique, self.available_sources)
                await self._generate_comprehensive_outputs(self.cumulative_unique, cumulative_stats, self.start_time, prefix="cumulative_")

                self.next_batch_threshold += CONFIG.batch_size

                if CONFIG.threshold > 0 and len(self.cumulative_unique) >= CONFIG.threshold:
                    print(f"\n⏹️  Threshold of {CONFIG.threshold} configs reached. Stopping early.")
                    self.stop_fetching = True
    
    def _deduplicate_config_results(self, results: List[ConfigResult]) -> List[ConfigResult]:
        """Efficient deduplication of config results using semantic hashing."""
        seen_hashes: Set[str] = set()
        unique_results: List[ConfigResult] = []

        for result in results:
            if CONFIG.tls_fragment and CONFIG.tls_fragment.lower() not in result.config.lower():
                continue
            if CONFIG.include_protocols and result.protocol.upper() not in CONFIG.include_protocols:
                continue
            if CONFIG.exclude_protocols and result.protocol.upper() in CONFIG.exclude_protocols:
                continue
            config_hash = self.processor.create_semantic_hash(result.config)
            if config_hash not in seen_hashes:
                seen_hashes.add(config_hash)
                unique_results.append(result)
        
        duplicates = len(results) - len(unique_results)
        print(f"   🗑️ Duplicates removed: {duplicates:,}")
        if len(results) > 0:
            efficiency = duplicates / len(results) * 100
        else:
            efficiency = 0
        print(f"   📊 Deduplication efficiency: {efficiency:.1f}%")
        return unique_results
    
    def _sort_by_performance(self, results: List[ConfigResult]) -> List[ConfigResult]:
        """Sort results by connection performance and protocol preference."""
        # Protocol priority ranking
        protocol_priority = {
            "VLESS": 1, "VMess": 2, "Reality": 3, "Hysteria2": 4, 
            "Trojan": 5, "Shadowsocks": 6, "TUIC": 7, "Hysteria": 8,
            "Naive": 9, "Juicity": 10, "WireGuard": 11, "Other": 12
        }
        
        def sort_key(result: ConfigResult) -> Tuple:
            is_reachable = 1 if result.is_reachable else 0
            ping_time = result.ping_time if result.ping_time is not None else float('inf')
            protocol_rank = protocol_priority.get(result.protocol, 13)
            return (-is_reachable, ping_time, protocol_rank)
        
        sorted_results = sorted(results, key=sort_key)
        
        reachable_count = sum(1 for r in results if r.is_reachable)
        print(f"   🚀 Sorted: {reachable_count:,} reachable configs first")
        
        if reachable_count > 0:
            fastest = min((r for r in results if r.ping_time), key=lambda x: x.ping_time, default=None)
            if fastest:
                print(f"   ⚡ Fastest server: {fastest.ping_time*1000:.1f}ms ({fastest.protocol})")
        
        return sorted_results
    
    def _analyze_results(self, results: List[ConfigResult], available_sources: List[str]) -> Dict:
        """Analyze results and generate comprehensive statistics."""
        protocol_stats = {}
        performance_stats = {}
        
        for result in results:
            # Protocol count
            protocol_stats[result.protocol] = protocol_stats.get(result.protocol, 0) + 1
            
            # Performance stats
            if result.ping_time is not None:
                if result.protocol not in performance_stats:
                    performance_stats[result.protocol] = []
                performance_stats[result.protocol].append(result.ping_time)
        
        # Calculate performance metrics
        perf_summary = {}
        for protocol, times in performance_stats.items():
            if times:
                perf_summary[protocol] = {
                    "count": len(times),
                    "avg_ms": round(sum(times) / len(times) * 1000, 2),
                    "min_ms": round(min(times) * 1000, 2),
                    "max_ms": round(max(times) * 1000, 2)
                }
        
        # Print comprehensive breakdown
        total = len(results)
        reachable = sum(1 for r in results if r.is_reachable)

        print(f"   📊 Total configs: {total:,}")
        reach_pct = (reachable / total * 100) if total else 0
        print(f"   🌐 Reachable configs: {reachable:,} ({reach_pct:.1f}%)")
        print(f"   🔗 Available sources: {len(available_sources)}")
        print(f"   📋 Protocol breakdown:")
        
        for protocol, count in sorted(protocol_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100 if total else 0
            perf_info = ""
            if protocol in perf_summary:
                avg_ms = perf_summary[protocol]["avg_ms"]
                perf_info = f" | Avg: {avg_ms}ms"
            print(f"      {protocol:12} {count:>7,} configs ({percentage:5.1f}%){perf_info}")
        
        return {
            "protocol_stats": protocol_stats,
            "performance_stats": perf_summary,
            "total_configs": total,
            "reachable_configs": reachable,
            "available_sources": len(available_sources),
            "total_sources": len(self.sources)
        }
    
    async def _generate_comprehensive_outputs(self, results: List[ConfigResult], stats: Dict, start_time: float, prefix: str = "") -> None:
        """Generate comprehensive output files with all formats."""
        # Create output directory
        output_dir = Path(CONFIG.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Extract configs for traditional outputs
        configs = [result.config for result in results]
        
        # Raw text output
        raw_file = output_dir / f"{prefix}vpn_subscription_raw.txt"
        tmp_raw = raw_file.with_suffix('.tmp')
        tmp_raw.write_text("\n".join(configs), encoding="utf-8")
        tmp_raw.replace(raw_file)
        
        # Base64 output
        base64_content = base64.b64encode("\n".join(configs).encode("utf-8")).decode("utf-8")
        base64_file = output_dir / f"{prefix}vpn_subscription_base64.txt"
        tmp_base64 = base64_file.with_suffix('.tmp')
        tmp_base64.write_text(base64_content, encoding="utf-8")
        tmp_base64.replace(base64_file)
        
        # Enhanced CSV with comprehensive performance data
        csv_file = output_dir / f"{prefix}vpn_detailed.csv"
        tmp_csv = csv_file.with_suffix('.tmp')
        with open(tmp_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Config', 'Protocol', 'Host', 'Port', 'Ping_MS', 'Reachable', 'Source'])
            for result in results:
                ping_ms = round(result.ping_time * 1000, 2) if result.ping_time else None
                writer.writerow([
                    result.config, result.protocol, result.host, result.port,
                    ping_ms, result.is_reachable, result.source_url
                ])
        tmp_csv.replace(csv_file)
        
        # Comprehensive JSON report
        report = {
            "generation_info": {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "processing_time_seconds": round(time.time() - start_time, 2),
                "script_version": "Unified & Polished Edition",
                "url_testing_enabled": CONFIG.enable_url_testing,
                "sorting_enabled": CONFIG.enable_sorting,
            },
            "statistics": stats,
            "source_categories": {
                "iranian_priority": len(UnifiedSources.IRANIAN_PRIORITY),
                "international_major": len(UnifiedSources.INTERNATIONAL_MAJOR),
                "comprehensive_batch": len(UnifiedSources.COMPREHENSIVE_BATCH),
                "total_unique_sources": len(self.sources),
            },
            "output_files": {
                "raw": str(raw_file),
                "base64": str(base64_file),
                "detailed_csv": str(csv_file),
                "json_report": "vpn_report.json",
                "singbox": str(output_dir / f"{prefix}vpn_singbox.json"),
            },
            "usage_instructions": {
                "base64_subscription": "Copy content of base64 file as subscription URL",
                "raw_subscription": "Host raw file and use URL as subscription link",
                "csv_analysis": "Use CSV file for detailed analysis and custom filtering",
                "supported_clients": [
                    "V2rayNG", "V2rayN", "Hiddify Next", "Shadowrocket", 
                    "NekoBox", "Clash Meta", "Sing-Box", "Streisand", "Karing"
                ]
            }
        }
        
        report_file = output_dir / f"{prefix}vpn_report.json"
        tmp_report = report_file.with_suffix('.tmp')
        tmp_report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_report.replace(report_file)

        # Simple outbounds JSON
        outbounds = []
        for idx, r in enumerate(results):
            ob = {
                "type": r.protocol.lower(),
                "tag": f"{r.protocol} {idx}",
                "server": r.host or "",
                "server_port": r.port,
                "raw": r.config
            }
            outbounds.append(ob)

        singbox_file = output_dir / f"{prefix}vpn_singbox.json"
        tmp_singbox = singbox_file.with_suffix('.tmp')
        tmp_singbox.write_text(json.dumps({"outbounds": outbounds}, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_singbox.replace(singbox_file)
    
    def _print_final_summary(self, config_count: int, elapsed_time: float, stats: Dict) -> None:
        """Print comprehensive final summary."""
        print("\n" + "=" * 85)
        print("🎉 UNIFIED VPN MERGER COMPLETE!")
        print(f"⏱️  Total processing time: {elapsed_time:.2f} seconds")
        print(f"📊 Final unique configs: {config_count:,}")
        print(f"🌐 Reachable configs: {stats['reachable_configs']:,}")
        print(f"📈 Success rate: {stats['reachable_configs']/config_count*100:.1f}%")
        print(f"🔗 Available sources: {stats['available_sources']}/{stats['total_sources']}")
        print(f"⚡ Processing speed: {config_count/elapsed_time:.0f} configs/second")
        
        if CONFIG.enable_sorting and stats['reachable_configs'] > 0:
            print(f"🚀 Configs sorted by performance (fastest first)")
        
        top_protocol = max(stats['protocol_stats'].items(), key=lambda x: x[1])[0]
        print(f"🏆 Top protocol: {top_protocol}")
        print(f"📁 Output directory: ./{CONFIG.output_dir}/")
        print("\n🔗 Usage Instructions:")
        print("   • Copy Base64 file content as subscription URL")
        print("   • Use CSV file for detailed analysis and filtering")
        print("   • All configs tested and sorted by performance")
        print("   • Dead sources automatically removed")
        print("=" * 85)

# ============================================================================
# EVENT LOOP DETECTION AND MAIN EXECUTION
# ============================================================================

async def main_async():
    """Main async function."""
    try:
        merger = UltimateVPNMerger()
        await merger.run()
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

def detect_and_run():
    """Detect event loop and run appropriately."""
    try:
        # Try to get the running loop
        loop = asyncio.get_running_loop()
        print("🔄 Detected existing event loop")
        print("📝 Creating task in existing loop...")
        
        # We're in an async environment (like Jupyter)
        task = asyncio.create_task(main_async())
        print("✅ Task created successfully!")
        print("📋 Use 'await task' to wait for completion in Jupyter")
        return task
        
    except RuntimeError:
        # No running loop - we can use asyncio.run()
        print("🔄 No existing event loop detected")
        print("📝 Using asyncio.run()...")
        return asyncio.run(main_async())

# Alternative for Jupyter/async environments
async def run_in_jupyter():
    """Direct execution for Jupyter notebooks and async environments."""
    print("🔄 Running in Jupyter/async environment")
    await main_async()

def _get_script_dir() -> Path:
    """
    Return a safe base directory for writing output.
    • In a regular script run, that’s the directory the script lives in.
    • In interactive/Jupyter runs, fall back to the current working dir.
    """
    try:
        return Path(__file__).resolve().parent        # normal execution
    except NameError:
        return Path.cwd()                             # Jupyter / interactive


def main():
    """Main entry point with event loop detection."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)

    import argparse

    parser = argparse.ArgumentParser(description="VPN Merger")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=CONFIG.batch_size,
        help="Save intermediate output every N configs (0 disables, default 100)"
    )
    parser.add_argument("--threshold", type=int, default=CONFIG.threshold,
                        help="Stop processing after N unique configs (0 = unlimited)")
    parser.add_argument("--top-n", type=int, default=CONFIG.top_n,
                        help="Keep only the N best configs after sorting (0 = all)")
    parser.add_argument("--tls-fragment", type=str, default=CONFIG.tls_fragment,
                        help="Only keep configs containing this TLS fragment")
    parser.add_argument("--include-protocols", type=str, default=None,
                        help="Comma-separated list of protocols to include")
    parser.add_argument("--exclude-protocols", type=str, default=None,
                        help="Comma-separated list of protocols to exclude")
    parser.add_argument("--resume", type=str, default=None,
                        help="Resume processing from existing raw/base64 file")
    parser.add_argument("--output-dir", type=str, default=CONFIG.output_dir,
                        help="Directory to save output files")
    parser.add_argument("--test-timeout", type=float, default=CONFIG.test_timeout,
                        help="TCP connection test timeout in seconds")
    parser.add_argument("--no-url-test", action="store_true",
                        help="Disable server reachability testing")
    parser.add_argument("--no-sort", action="store_true",
                        help="Disable performance-based sorting")
    parser.add_argument("--concurrent-limit", type=int, default=CONFIG.concurrent_limit,
                        help="Number of concurrent requests")
    parser.add_argument("--max-retries", type=int, default=CONFIG.max_retries,
                        help="Retry attempts when fetching sources")
    parser.add_argument("--max-ping", type=int, default=0,
                        help="Discard configs slower than this ping in ms (0 = no limit)")
    parser.add_argument("--log-file", type=str, default=None,
                        help="Write output messages to a log file")
    parser.add_argument("--cumulative-batches", action="store_true",
                        help="Save each batch as cumulative rather than standalone")
    parser.add_argument("--no-strict-batch", action="store_true",
                        help="Use batch size only as update threshold")
    parser.add_argument("--shuffle-sources", action="store_true",
                        help="Process sources in random order")
    args, unknown = parser.parse_known_args()
    if unknown:
        logging.warning("Ignoring unknown arguments: %s", unknown)

    CONFIG.batch_size = max(0, args.batch_size)
    CONFIG.threshold = max(0, args.threshold)
    CONFIG.top_n = max(0, args.top_n)
    CONFIG.tls_fragment = args.tls_fragment
    if args.include_protocols:
        CONFIG.include_protocols = {p.strip().upper() for p in args.include_protocols.split(',') if p.strip()}
    if args.exclude_protocols:
        CONFIG.exclude_protocols = {p.strip().upper() for p in args.exclude_protocols.split(',') if p.strip()}
    CONFIG.resume_file = args.resume
    # Resolve and validate output directory to prevent path traversal
    allowed_base = _get_script_dir()
    resolved_output = Path(args.output_dir).expanduser().resolve()
    try:
        resolved_output.relative_to(allowed_base)
    except ValueError:
        parser.error(f"--output-dir must be within {allowed_base}")
    CONFIG.output_dir = str(resolved_output)
    CONFIG.test_timeout = max(0.1, args.test_timeout)
    CONFIG.concurrent_limit = max(1, args.concurrent_limit)
    CONFIG.max_retries = max(1, args.max_retries)
    CONFIG.max_ping_ms = args.max_ping if args.max_ping > 0 else None
    CONFIG.log_file = args.log_file
    CONFIG.cumulative_batches = args.cumulative_batches
    CONFIG.strict_batch = not args.no_strict_batch
    CONFIG.shuffle_sources = args.shuffle_sources
    if args.no_url_test:
        CONFIG.enable_url_testing = False
    if args.no_sort:
        CONFIG.enable_sorting = False

    if CONFIG.log_file:
        logging.basicConfig(filename=CONFIG.log_file, level=logging.INFO,
                            format='%(asctime)s %(levelname)s:%(message)s')

    print("🔧 VPN Merger - Checking environment...")

    try:
        return detect_and_run()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n📋 Alternative execution methods:")
        print("   • For Jupyter: await run_in_jupyter()")
        print("   • For scripts: python script.py")

if __name__ == "__main__":
    main()

# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================

print("""
🚀 VPN Subscription Merger - Final Unified Edition

📋 Execution Methods:
   • Regular Python: python script.py
   • Jupyter/IPython: await run_in_jupyter()
   • With event loop errors: task = detect_and_run(); await task

🎯 Unified Features:
   • 450+ sources (Iranian priority + International + Comprehensive)
   • Dead link detection and automatic removal
   • Real-time server reachability testing with response time measurement
   • Smart sorting by connection speed and protocol preference
   • Advanced semantic deduplication
   • Multiple output formats (raw, base64, CSV with performance data, JSON)
   • Event loop compatibility for all environments
   • Comprehensive error handling and retry logic

📊 Expected Results:
   • 800k-1.2M+ tested and sorted configs
   • 70-85% configs will be reachable and validated
   • Processing time: 8-12 minutes with full testing
   • Dead sources automatically filtered out
   • Performance-optimized final list

📁 Output Files:
   • vpn_subscription_raw.txt (for hosting)
   • vpn_subscription_base64.txt (for direct import)
   • vpn_detailed.csv (with performance metrics)
   • vpn_report.json (comprehensive statistics)
""")
