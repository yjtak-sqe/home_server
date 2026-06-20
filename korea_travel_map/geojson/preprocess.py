"""
시/군/구 GeoJSON을 시/군 단위로 병합하는 전처리 스크립트.
실행: python preprocess.py
"""
import geopandas as gpd
import json

# 광역시/특별시/특별자치시: 코드 앞 2자리 → 시 이름
# 실제 데이터: 서울=11, 부산=21, 대구=22, 인천=23, 광주=24, 대전=25, 울산=26, 세종=29
METRO = {
    "11": "서울특별시",
    "21": "부산광역시",
    "22": "대구광역시",
    "23": "인천광역시",
    "24": "광주광역시",
    "25": "대전광역시",
    "26": "울산광역시",
    "29": "세종특별자치시",
}

# 도내 구가 있는 시: 코드 앞 4자리 → 시 이름
# 실제 데이터 기준 (5자리 코드)
GU_TO_SI = {
    "3101": "수원시",
    "3102": "성남시",
    "3104": "안양시",
    "3109": "안산시",
    "3110": "고양시",
    "3119": "용인시",
    "3304": "청주시",
    "3401": "천안시",
    "3501": "전주시",
    "3701": "포항시",
    "3811": "창원시",
}

def get_merge_key(row) -> str:
    code = str(row["code"]).zfill(5)
    name = row["name"]

    # 광역시/특별시 내 구 → 시 단위로
    if code[:2] in METRO:
        return METRO[code[:2]]

    # 도내 시 내 구 → 시 단위로
    if code[:4] in GU_TO_SI:
        return GU_TO_SI[code[:4]]

    return name


gdf = gpd.read_file("raw_sigungu.geojson")
gdf["merge_key"] = gdf.apply(get_merge_key, axis=1)
merged = gdf.dissolve(by="merge_key").reset_index()[["merge_key", "geometry"]]
merged = merged.rename(columns={"merge_key": "name"})
merged.to_file("korea_sigun.geojson", driver="GeoJSON")
print(f"완료: {len(merged)}개 단위 생성")
