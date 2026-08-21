PERFIS_NORMALIZACAO = {

    "padrao": {
        "mapa_colunas": {
            "data_hora": "data_hora",
            "status_bomba": "status_bomba",
            "tensao_v": "tensao_v",
            "corrente_a": "corrente_a",
            "temp_mancal_c": "temp_mancal_c",
            "vibracao_mm_s": "vibracao_mm_s",
            "nivel_pct": "nivel_pct",
            "alarme": "alarme"
        },

        "conversoes": {
            "tensao": None,
            "temperatura": None,
            "nivel": None
        }
    },

    "heterogeneo": {
        "mapa_colunas": {
            "Timestamp": "data_hora",
            "Pump_Status": "status_bomba",
            "Voltage_kV": "tensao_v",
            "Current_A": "corrente_a",
            "Bearing_Temp_F": "temp_mancal_c",
            "Vibration_mm_s": "vibracao_mm_s",
            "Tank_Level_fraction": "nivel_pct",
            "Alarm": "alarme"
        },

        "conversoes": {
            "tensao": "kv_para_v",
            "temperatura": "f_para_c",
            "nivel": "fracao_para_pct"
        }
    },

    "pi_simulado": {
        "mapa_colunas": {
            "Timestamp": "data_hora",
            "Running": "status_bomba",
            "Voltage": "tensao_v",
            "Current": "corrente_a",
            "BearingTemperature": "temp_mancal_c",
            "Vibration": "vibracao_mm_s",
            "Level": "nivel_pct",
            "Alarm": "alarme"
        },

        "conversoes": {
            "tensao": None,
            "temperatura": None,
            "nivel": None
        }
    }
}