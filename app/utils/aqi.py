"""
aqi.py
=======
Fungsi bantu untuk mengklasifikasikan nilai PM2.5 ke kategori ISPU resmi
(Permen LHK No. 14/2020), sesuai breakpoint yang dipublikasikan BMKG.
"""
from app.config import ISPU_BREAKPOINTS


def classify_pm25(value: float) -> dict:
    """
    Mengembalikan dict {label, color, emoji, level} untuk satu nilai PM2.5.
    `level` adalah indeks 0-4 (0=Baik ... 4=Berbahaya), berguna untuk sorting/warna gradient.
    """
    if value is None:
        return {"label": "TIDAK ADA DATA", "color": "#94a3b8", "emoji": "⚪", "level": -1}

    for level, (low, high, label, color, emoji) in enumerate(ISPU_BREAKPOINTS):
        if low <= value <= high:
            return {"label": label, "color": color, "emoji": emoji, "level": level}
    # Nilai di atas batas tertinggi
    _, _, label, color, emoji = ISPU_BREAKPOINTS[-1]
    return {"label": label, "color": color, "emoji": emoji, "level": len(ISPU_BREAKPOINTS) - 1}


def get_recommendation(label: str) -> str:
    recommendations = {
        "BAIK": "Kualitas udara sangat baik. Aktivitas luar ruangan aman untuk semua kelompok.",
        "SEDANG": "Kualitas udara masih dapat diterima. Kelompok sensitif (anak-anak, lansia, "
                   "penderita gangguan pernapasan) disarankan mengurangi aktivitas luar ruangan yang berat.",
        "TIDAK SEHAT": "Kelompok sensitif berisiko mengalami gangguan kesehatan. Gunakan masker "
                        "saat beraktivitas di luar ruangan dan batasi durasinya.",
        "SANGAT TIDAK SEHAT": "Seluruh populasi berisiko mengalami gangguan kesehatan. Hindari "
                               "aktivitas luar ruangan, gunakan masker N95, dan pertimbangkan air purifier di dalam ruangan.",
        "BERBAHAYA": "Kondisi darurat kesehatan. Tetap di dalam ruangan, tutup ventilasi, dan "
                      "ikuti arahan resmi dari otoritas setempat.",
        "TIDAK ADA DATA": "Data belum tersedia untuk periode ini.",
    }
    return recommendations.get(label, "Data tidak tersedia.")
