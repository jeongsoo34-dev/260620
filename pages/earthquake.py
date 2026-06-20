import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(page_title="Global Earthquake Tracker", layout="wide")

st.title("🌍 전세계 지진 데이터 시각화 웹 앱")
st.markdown("USGS API를 활용하여 전세계에서 발생한 실시간 및 과거 지진 데이터를 시각화합니다.")

# --- 사이드바 컨트롤러 ---
st.sidebar.header("🔍 필터 설정")

# 연도 선택 (1970년부터 현재 연도까지)
current_year = datetime.now().year
selected_year = st.sidebar.selectbox("조회할 연도를 선택하세요", list(range(current_year, 1969, -1)))

# 최소 지진 규모 선택 (과도한 데이터 로딩 방지 및 유의미한 데이터 필터링)
min_magnitude = st.sidebar.slider("최소 지진 규모 (Magnitude)", 1.0, 9.0, 5.0, 0.5)

# --- 데이터 가져오기 함수 ---
@st.cache_data
def get_earthquake_data(year, min_mag):
    # USGS API Endpoint (시간 범위 지정: YYYY-MM-DD)
    start_time = f"{year}-01-01"
    end_time = f"{year}-12-31"
    url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={start_time}&endtime={end_time}&minmagnitude={min_mag}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        # GeoJSON을 Pandas DataFrame으로 가공
        features = data['features']
        if not features:
            return pd.DataFrame()
            
        earthquakes = []
        for f in features:
            props = f['properties']
            geom = f['geometry']
            
            # 밀리초 단위를 가독성 있는 날짜로 변경
            time_epoch = props['time'] / 1000
            time_formatted = datetime.fromtimestamp(time_epoch).strftime('%Y-%m-%d %H:%M:%S')
            
            earthquakes.append({
                "place": props['place'],
                "mag": props['mag'],
                "time": time_formatted,
                "lon": geom['coordinates'][0],
                "lat": geom['coordinates'][1],
                "depth": geom['coordinates'][2]
            })
        return pd.DataFrame(earthquakes)
    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

# 데이터 로딩 스피너
with st.spinner(f"{selected_year}년의 지진 데이터를 가져오는 중..."):
    df = get_earthquake_data(selected_year, min_magnitude)

# --- 메인 대시보드 화면 ---
if not df.empty:
    # 요약 통계 메트릭 표시
    col1, col2, col3 = st.columns(3)
    col1.metric("총 발생 건수", f"{len(df)} 건")
    col2.metric("최대 규모", f"{df['mag'].max()} M")
    col3.metric("평균 깊이", f"{df['depth'].mean():.1f} km")

    # 지도 레이아웃
    st.subheader(f"🗺️ {selected_year}년 지진 발생 위치 지도 (규모 {min_magnitude} 이상)")
    
    # Folium 기본 지도 생성 (전세계를 볼 수 있도록 위경도 0,0 중심)
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB positron")
    
    # 지진 위치 마커 추가
    for _, row in df.iterrows():
        # 지진 규모에 따라 마커 크기 및 색상 동적 조절
        radius = row['mag'] * 2.5
        if row['mag'] >= 7.0:
            color = "#800026"  # 매우 강함 (짙은 빨강)
        elif row['mag'] >= 6.0:
            color = "#E31A1C"  # 강함 (빨강)
        else:
            color = "#FC4E2A"  # 보통 (주황)

        popup_text = f"""
        <strong>위치:</strong> {row['place']}<br>
        <strong>규모:</strong> {row['mag']}<br>
        <strong>시간:</strong> {row['time']}<br>
        <strong>깊이:</strong> {row['depth']} km
        """
        
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(m)

    # 스트림릿에 Folium 지도 렌더링
    st_folium(m, width="100%", height=500, returned_objects=[])

    # 데이터 테이블 표시
    st.subheader("📊 상세 데이터 테이블")
    st.dataframe(df[['time', 'mag', 'place', 'depth', 'lat', 'lon']], use_container_width=True)
else:
    st.info(f"선택한 조건({selected_year}년, 규모 {min_magnitude} 이상)에 해당하는 지진 데이터가 없습니다.")
