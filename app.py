# app.py —— 奇门遁甲排盘 API v1.3（转盘法终极修正版）
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lunar_python import Solar

app = FastAPI(title="奇门遁甲排盘 API", version="1.3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PALACE = {1:"坎",2:"坤",3:"震",4:"巽",5:"中",6:"乾",7:"兑",8:"艮",9:"离"}
STAR   = {1:"天蓬",2:"天芮",3:"天冲",4:"天辅",5:"天禽",6:"天心",7:"天柱",8:"天任",9:"天英"}
DOOR   = {1:"休门",2:"死门",3:"伤门",4:"杜门",6:"开门",7:"惊门",8:"生门",9:"景门"}
GAN    = "甲乙丙丁戊己庚辛壬癸"
ZHI    = "子丑寅卯辰巳午未申酉戌亥"
LIUYI  = "戊己庚辛壬癸丁丙乙"

JIEQI_JU = {
 "冬至":("阳",1,7,4),"小寒":("阳",2,8,5),"大寒":("阳",3,9,6),
 "立春":("阳",8,5,2),"雨水":("阳",9,6,3),"惊蛰":("阳",1,7,4),
 "春分":("阳",3,9,6),"清明":("阳",4,1,7),"谷雨":("阳",5,2,8),
 "立夏":("阳",4,1,7),"小满":("阳",5,2,8),"芒种":("阳",6,3,9),
 "夏至":("阴",9,3,6),"小暑":("阴",8,2,5),"大暑":("阴",7,1,4),
 "立秋":("阴",2,5,8),"处暑":("阴",1,4,7),"白露":("阴",9,3,6),
 "秋分":("阴",7,1,4),"寒露":("阴",6,9,3),"霜降":("阴",5,8,2),
 "立冬":("阴",6,9,3),"小雪":("阴",5,8,2),"大雪":("阴",4,7,1),
}
KONG = {0:"戌亥",10:"申酉",20:"午未",30:"辰巳",40:"寅卯",50:"子丑"}
PALACE_ZHI = {1:"子",2:"未申",3:"卯",4:"辰巳",5:"",6:"戌亥",7:"酉",8:"丑寅",9:"午"}
MA = {8:"寅",0:"寅",4:"寅",2:"申",6:"申",10:"申",
      5:"亥",9:"亥",1:"亥",11:"巳",3:"巳",7:"巳"}

# 后天八卦（周天）轨迹：1->8->3->4->9->2->7->6->1
ORBIT = [1, 8, 3, 4, 9, 2, 7, 6]

def _60(gan: str, zhi: str) -> int:
    g, z = GAN.index(gan), ZHI.index(zhi)
    for i in range(60):
        if i % 10 == g and i % 12 == z:
            return i
    return -1

def build_chart(y, m, d, h, mi):
    solar = Solar.fromYmdHms(y, m, d, h, mi, 0)
    lunar = solar.getLunar()

    # 1. 四柱
    sizhu = (lunar.getYearInGanZhi(), lunar.getMonthInGanZhi(),
             lunar.getDayInGanZhi(), lunar.getTimeInGanZhi())

    # 2. 节气
    try:
        jq = lunar.getPrevJieQi().getName()
    except Exception:
        jq = "冬至"
    if jq not in JIEQI_JU:
        for k in JIEQI_JU:
            if k in jq:
                jq = k
                break
        else:
            jq = "冬至"

    # 3. 定元（拆补法）
    dg, dz = GAN.index(lunar.getDayGan()), ZHI.index(lunar.getDayZhi())
    dist = dg % 5
    futou_zhi = (dz - dist) % 12
    if futou_zhi in (0, 6, 3, 9):
        yuan = 0
    elif futou_zhi in (2, 8, 5, 11):
        yuan = 1
    else:
        yuan = 2

    dun, j1, j2, j3 = JIEQI_JU[jq]
    ju = [j1, j2, j3][yuan]

    # 4. 地盘三奇六仪
    seq = list(range(1, 10)) if dun == "阳" else list(range(9, 0, -1))
    start = seq.index(ju)
    dipan = {}
    for i, g in enumerate(LIUYI):
        dipan[seq[(start + i) % 9]] = g

    # 5. 旬首、值符、值使
    tg_name, tz_name = lunar.getTimeGan(), lunar.getTimeZhi()
    t60 = _60(tg_name, tz_name)
    xs = t60 - (t60 % 10)
    xun_liuyi = "戊己庚辛壬癸"[xs // 10]
    zhifu_gong = next(p for p, g in dipan.items() if g == xun_liuyi)
    zhishi_gong = zhifu_gong if zhifu_gong != 5 else 2
    zhifu_star_name = STAR[zhifu_gong]
    zhishi_door_name = DOOR.get(zhishi_gong, "死门")

    # 值符飞到时干地盘宫（甲用旬首代替）
    tg_for_pan = xun_liuyi if tg_name == "甲" else tg_name
    target_gong = next((p for p, g in dipan.items() if g == tg_for_pan), zhifu_gong)
    if target_gong == 5:
        target_gong = 2

    # ================= 九星与天盘干（沿 ORBIT 旋转） =================
    star_home = {1:"天蓬",8:"天任",3:"天冲",4:"天辅",9:"天英",2:"天芮",7:"天柱",6:"天心"}
    zf_idx = ORBIT.index(zhifu_gong if zhifu_gong != 5 else 2)
    tg_idx = ORBIT.index(target_gong)
    star_shift = (tg_idx - zf_idx) % 8 if dun == "阳" else (zf_idx - tg_idx) % 8

    star_pan = {}
    tianpan = {}
    for i, home in enumerate(ORBIT):
        new_gong = ORBIT[(i + star_shift) % 8] if dun == "阳" else ORBIT[(i - star_shift) % 8]
        star_pan[new_gong] = star_home[home]
        tianpan[new_gong] = dipan[home]  # 天盘干随星走，即原宫地盘干
    
    # 天禽星寄宫处理（天禽永远跟天芮同行，天盘干加上天禽原宫干，通常是戊或己）
    # 找到天芮落宫
    rui_gong = [k for k, v in star_pan.items() if v == "天芮"][0]
    qin_gan = dipan.get(5, "")
    if qin_gan:
        tianpan[rui_gong] = f"{tianpan[rui_gong]}---{qin_gan}"
    star_pan[rui_gong] = "芮禽"
    # 中5宫处理
    star_pan[5] = "天禽"
    tianpan[5] = ""

    # ================= 八门（沿 ORBIT 旋转） =================
    door_home = {1:"休门",8:"生门",3:"伤门",4:"杜门",9:"景门",2:"死门",7:"惊门",6:"开门"}
    orig_zs_idx = ORBIT.index(zhishi_gong)
    new_zs_idx = ORBIT.index(target_gong if target_gong != 5 else 2)
    
    # 八门也有自己的目标落宫（按宫数顺/逆飞）
    door_step = t60 - xs
    door_seq = [1, 2, 3, 4, 6, 7, 8, 9]
    si = door_seq.index(zhishi_gong)
    ti = (si + door_step) % 8 if dun == "阳" else (si - door_step) % 8
    new_zhishi_gong = door_seq[ti]
    
    # 八门整体沿 ORBIT 顺时针旋转
    zs_idx = ORBIT.index(zhishi_gong)
    ns_idx = ORBIT.index(new_zhishi_gong)
    door_shift = (ns_idx - zs_idx) % 8

    door_pan = {}
    for i, home in enumerate(ORBIT):
        new_gong = ORBIT[(i + door_shift) % 8]
        door_pan[new_gong] = door_home[home]

    door_pan[5] = "—"

    # ================= 八神（从值符落宫起排） =================
    shen_names = ["值符","腾蛇","太阴","六合","白虎","玄武","九地","九天"]
    zf_new_idx = ORBIT.index(target_gong)
    shen_pan = {}
    for i, name in enumerate(shen_names):
        p = ORBIT[(zf_new_idx + i) % 8] if dun == "阳" else ORBIT[(zf_new_idx - i) % 8]
        shen_pan[p] = name
    shen_pan[5] = ""

    # 空亡 / 马星
    kong = KONG[xs]
    ma = MA[ZHI.index(tz_name)]

    # 组装九宫
    gongs = []
    for p in range(1, 10):
        gongs.append({
            "宫位": f"{PALACE[p]}{p}宫",
            "宫数": p,
            "天盘干": tianpan.get(p, ""),
            "地盘干": dipan.get(p, ""),
            "九星": star_pan.get(p, ""),
            "八门": door_pan.get(p, "—"),
            "八神": shen_pan.get(p, ""),
            "空亡": "是" if set(PALACE_ZHI[p]) & set(kong) else "否",
        })

    return {
        "四柱": {"年": sizhu[0], "月": sizhu[1], "日": sizhu[2], "时": sizhu[3]},
        "节气": jq,
        "元": ["上元","中元","下元"][yuan],
        "阴阳遁": dun + "遁",
        "局数": f"{dun}遁{ju}局",
        "值符": zhifu_star_name,
        "值使": zhishi_door_name,
        "旬首": f"甲{xun_liuyi}",
        "空亡": kong,
        "马星": ma,
        "九宫": gongs,
        "备注": "中5宫天禽寄坤2；盘面请与元亨利贞排盘网核对",
    }


@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/qimen")
def qimen(datetime_str: str, gender: str = "男"):
    try:
        dt = datetime_str.replace("T", " ").strip()
        date_part, time_part = dt.split(" ")[0], dt.split(" ")[1]
        y, m, d = [int(x) for x in date_part.split("-")]
        hh, mm = [int(x) for x in time_part.split(":")]
    except Exception:
        return {"error": "时间格式应为 2024-06-01 14:30"}
    res = build_chart(y, m, d, hh, mm)
    res["求测人性别"] = gender
    return res