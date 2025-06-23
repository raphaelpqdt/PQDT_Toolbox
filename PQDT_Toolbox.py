# ==============================================================================
# Predadores Multi-Tool - Versão Unificada
# Combina o Auto-Restarter e o Votemap Bypass em uma única aplicação com abas.
# ADIÇÃO: Sistema de tradução (PT-BR / EN-US) e menu para seleção de idioma.
# ADIÇÃO: Central de Notificações com Toasts customizados.
# ==============================================================================

import os
import re
import time
import threading
import random
import json
import sqlite3
import subprocess
import logging
import platform
import tkinter as tk
from tkinter import simpledialog, messagebox
import sys
import webbrowser
from datetime import datetime
import shutil
from collections import deque

# --- Tratamento de Dependências Opcionais ---
try:
    import pystray
    from PIL import Image, ImageTk, ImageDraw

    PIL_AVAILABLE = True
    PYSTRAY_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    PYSTRAY_AVAILABLE = False
    pystray = None
    Image = None
    ImageTk = None
    ImageDraw = None
    logging.warning(
        "Pillow (PIL) ou pystray não encontrados. Funcionalidades de ícone e bandeja estarão limitadas/desabilitadas.")

try:
    import win32com.client
    import pythoncom

    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False

SYSTEMCTL_AVAILABLE = platform.system() == "Linux" and shutil.which('systemctl') is not None

# --- Módulos Tkinter ---
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from ttkbootstrap.dialogs import Messagebox
from tkinter import filedialog
from tkinter.scrolledtext import ScrolledText

# --- Configuração do Logging ---
LOG_FILENAME_RESTARTER = "restarter_tool.log"
LOG_FILENAME_VOTEMAP = "votemap_tool.log"

log_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - [%(threadName)s] - %(module)s.%(funcName)s:%(lineno)d - %(message)s')

restarter_handler = logging.FileHandler(LOG_FILENAME_RESTARTER, mode='a', encoding='utf-8')
restarter_handler.setFormatter(log_formatter)
restarter_logger = logging.getLogger('RestarterTool')
restarter_logger.setLevel(logging.DEBUG)
restarter_logger.addHandler(restarter_handler)

votemap_handler = logging.FileHandler(LOG_FILENAME_VOTEMAP, mode='a', encoding='utf-8')
votemap_handler.setFormatter(log_formatter)
votemap_logger = logging.getLogger('VotemapTool')
votemap_logger.setLevel(logging.INFO)
votemap_logger.addHandler(votemap_handler)

app_logger = logging.getLogger('UnifiedApp')
app_logger.setLevel(logging.INFO)
app_handler = logging.StreamHandler(sys.stdout)
app_handler.setFormatter(log_formatter)
app_logger.addHandler(app_handler)


# --- Constantes e Funções de Recurso ---
def resource_path(relative_path):
    """ Retorna o caminho absoluto para o recurso, funciona para dev e para PyInstaller """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


ICON_FILENAME = "pred.ico"
BACKGROUND_IMAGE_FILENAME = "pred.png"
BACKGROUND_ALPHA_MULTIPLIER = 0.15

ICON_PATH = resource_path(ICON_FILENAME)
BACKGROUND_IMAGE_PATH = resource_path(BACKGROUND_IMAGE_FILENAME)


# ==============================================================================
# SISTEMA DE TRADUÇÃO (I18N)
# ==============================================================================
class I18N:
    """ Gerencia as traduções da aplicação. """

    def __init__(self, language='pt-br'):
        self.language = language
        self.translations = self.get_full_translation_dict()

    def set_language(self, language):
        if language in self.translations:
            self.language = language
            app_logger.info(f"Idioma alterado para: {language}")
        else:
            app_logger.warning(f"Idioma '{language}' não encontrado. Mantendo '{self.language}'.")

    def get(self, key, **kwargs):
        try:
            val = self.translations[self.language].get(key, key)
            if kwargs:
                return val.format(**kwargs)
            return val
        except KeyError:
            val = self.translations['en-us'].get(key, key)
            if kwargs:
                return val.format(**kwargs)
            return val
        except Exception:
            return key

    def get_full_translation_dict(self):
        return {
            'pt-br': {
                # Main App & Menus
                "app_title": "PQDT_Raphael - ArmaServerToolbox", "menu_language": "Idioma", "menu_file": "Arquivo",
                "menu_save_config": "Salvar Configuração", "menu_exit": "Sair", "menu_restarter": "Auto-Restarter",
                "menu_add_server": "Adicionar Servidor", "menu_rename_server": "Renomear Servidor",
                "menu_remove_current_server": "Remover Servidor Atual", "menu_votemap": "Votemap Bypass",
                "menu_tools": "Ferramentas", "menu_change_theme": "Mudar Tema", "menu_collect_player_info": "Coletar Info Jogadores", "menu_help": "Ajuda",
                "menu_about": "Sobre",
                "tab_top_restarter": "Auto-Restarter", "tab_top_votemap": "Votemap Bypass",
                "tab_system_log": "Log do Sistema",
                "status_ready": "Pronto.", "status_config_saved": "Configuração salva!",
                "status_service_selected": "Serviço '{service}' selecionado para '{server}'.",
                "status_server_removed": "Servidor '{server}' ({tool}) removido.",
                "status_server_renamed": "Servidor renomeado para '{name}'.",
                "dialog_rename_server_title": "Renomear '{server}'",
                "dialog_rename_server_prompt": "Digite o novo nome para o servidor:",
                "dialog_rename_error_empty_title": "Nome Inválido",
                "dialog_rename_error_empty_msg": "O nome do servidor não pode ser vazio.",
                "dialog_rename_error_duplicate_title": "Nome Duplicado",
                "dialog_rename_error_duplicate_msg": "O nome '{name}' já está em uso nesta ferramenta.",
                "about_title": "Sobre / About",
                "about_message": (
                    "Esta é uma aplicação unificada que combina as funcionalidades do Auto-Restarter e do Votemap Bypass.\n\n"
                    "Use as abas superiores para alternar entre as ferramentas.\n"
                    "Cada ferramenta pode gerenciar múltiplos servidores em suas próprias abas internas.\n\n"
                    "Desenvolvido por PQDT_Raphael para a comunidade Predadores Brasil e KOTH Reforged."
                    "\n\n---\n\n"
                    "This is a unified application that combines the features of the Auto-Restarter and the Votemap Bypass.\n\n"
                    "Use the top tabs to switch between tools.\n"
                    "Each tool can manage multiple servers in its own internal tabs.\n\n"
                    "Developed by PQDT_Raphael for Predadores Brasil and KOTH Reforged community."
                ),
                "default_server_name": "Servidor {count}", "btn_select_log_folder": "Pasta de Logs",
                "tooltip_select_log_folder": "Seleciona a pasta raiz onde os logs do servidor são armazenados.",
                "btn_select_service": "Selecionar Serviço",
                "tooltip_select_service": "Seleciona o serviço associado ao servidor (Windows ou Linux).",
                "btn_start_service": "▶ Iniciar Serviço",
                "tooltip_start_service": "Tenta iniciar o serviço selecionado.",
                "btn_stop_service": "■ Parar Serviço", "tooltip_stop_service": "Tenta parar o serviço selecionado.",
                "btn_refresh_status": "↻", "tooltip_refresh_status": "Atualizar status do serviço selecionado.",
                "lbl_log_folder_prefix": "Pasta Logs", "lbl_service_prefix": "Serviço", "status_none": "Nenhuma",
                "status_invalid": "INVÁLIDA", "status_not_found_short": "NÃO ENC.",
                "status_not_found_long": "(Não encontrado!)",
                "status_checking": "(Verificando...)", "status_running_win": "(Rodando)",
                "status_stopped_win": "(Parado)",
                "status_starting_win": "(Iniciando...)", "status_stopping_win": "(Parando...)",
                "status_error": "(Erro!)",
                "status_unknown": "(Desconhecido)", "status_active_linux": "(Ativo)",
                "status_inactive_linux": "(Inativo)",
                "status_failed_linux": "(Falhou)", "status_activating_linux": "(Ativando...)",
                "status_deactivating_linux": "(Desativando...)",
                "na_pywin32": "N/A (pywin32)", "na_systemctl": "N/A (systemctl)", "na_os": "N/A (SO {os})",
                "lbl_log_controls": "Controles de Log", "lbl_filter": "Filtro:",
                "tooltip_filter": "Filtra novas linhas de log (case-insensitive).",
                "btn_pause": "⏸️ Pausar", "btn_resume": "▶️ Retomar",
                "tooltip_pause_resume": "Pausa ou retoma o acompanhamento ao vivo dos logs.",
                "btn_clear_log": "♻️ Limpar", "tooltip_clear_log": "Limpa a área de exibição de logs do servidor.",
                "btn_restart_monitor": "↻ Mon.",
                "tooltip_restart_monitor": "Força o reinício do monitor de logs desta aba.",
                "lbl_server_logs": "Logs do Servidor", "lbl_live_log": "LOG AO VIVO DO SERVIDOR",
                "lbl_search": "Buscar:",
                "btn_next": "Próximo", "btn_previous": "Anterior", "btn_close_search": "X",
                "chk_auto_scroll": "Rolar Auto.",
                "chk_system_log_auto_scroll": "Rolar Auto.", "lbl_stop_delay": "Delay Parar Serviço (s):",
                "tooltip_stop_delay_win": "Tempo (s) para aguardar após comando de parada do serviço.",
                "lbl_start_delay": "Delay Iniciar Serviço (s):",
                "tooltip_start_delay_win": "Tempo (s) para aguardar o serviço iniciar completamente.",
                "dialog_select_folder_title": "Selecione a pasta de logs para '{server}'",
                "dialog_unsupported_os_title": "Não Suportado",
                "dialog_unsupported_os_msg": "Gerenciamento de serviços não suportado em {os}.",
                "dialog_remove_server_title": "Remover '{server}'?",
                "dialog_remove_server_msg": "Tem certeza que deseja remover o servidor '{server}' da ferramenta {tool}?",
                "dialog_invalid_action_title": "Ação Inválida",
                "dialog_invalid_action_msg": "Selecione uma aba de servidor para realizar esta ação.",
                "dialog_theme_error_title": "Erro de Tema",
                "dialog_theme_error_msg": "Não foi possível aplicar o tema '{theme}'.",
                "dialog_save_error_title": "Erro ao Salvar", "dialog_save_error_msg": "Erro: {error}",
                "warn_no_service_selected_title": "Nenhum Serviço",
                "warn_no_service_to_stop": "Selecione um serviço para parar.",
                "warn_no_service_to_start": "Selecione um serviço para iniciar.",
                "info_service_stopped_title": "Serviço Parado",
                "info_service_stopped_msg": "O serviço '{service}' foi parado.",
                "error_service_stop_failed_title": "Falha ao Parar",
                "error_service_stop_failed_msg": "Não foi possível parar o serviço '{service}'. Verifique os logs.",
                "info_service_started_title": "Serviço Iniciado",
                "info_service_started_msg": "O serviço '{service}' foi iniciado.",
                "error_service_start_failed_title": "Falha ao Iniciar",
                "error_service_start_failed_msg": "Não foi possível iniciar o serviço '{service}'. Verifique os logs.",
                "log_manual_stop": "--- PARANDO SERVIÇO '{service}' MANUALMENTE ---",
                "log_manual_start": "--- INICIANDO SERVIÇO '{service}' MANUALMENTE ---",
                "log_executing_sc_stop": "Executando 'sc stop {service}'...",
                "log_executing_sysd_stop": "Executando 'systemctl stop {service}'...",
                "log_unsupported_os_control": "ERRO: Sistema operacional '{os}' não suportado para controle de serviço.",
                "log_stop_cmd_sent": "Comando de parada para '{service}' enviado com sucesso.",
                "log_stop_error": "ERRO ao parar serviço '{service}': {error}",
                "log_executing_sc_start": "Executando 'sc start {service}'...",
                "log_executing_sysd_start": "Executando 'systemctl start {service}'...",
                "log_start_cmd_sent": "Comando de início para '{service}' enviado com sucesso.",
                "log_start_error": "ERRO ao iniciar serviço '{service}': {error}",
                "dialog_missing_component_title": "Componente Ausente",
                "dialog_missing_pywin32": "pywin32 é necessário para listar serviços do Windows.",
                "dialog_missing_systemctl": "systemctl é necessário para listar serviços do Linux.",
                "dialog_loading_services_title": "Carregando Serviços ({os})",
                "dialog_loading_services_msg": "Aguarde...", "dialog_wmi_error_title": "Erro WMI",
                "dialog_wmi_error_msg": "Falha ao listar serviços: {error}",
                "dialog_systemctl_error_title": "Erro systemctl",
                "dialog_systemctl_error_msg": "Falha ao listar serviços: {error}",
                "dialog_no_services_found_title": "Nenhum Serviço",
                "dialog_no_services_found_msg": "Nenhum serviço gerenciável encontrado para {os}.",
                "dialog_select_service_title": "Selecionar Serviço para '{server}'",
                "dialog_service_name_header": "Nome do Serviço ({os})", "btn_confirm": "Confirmar",
                "btn_cancel": "Cancelar",
                "restarter_tab_paths_and_service": "Configuração de Caminhos e Serviço",
                "restarter_tab_options": "Opções de Reinício (Gatilho)",
                "restarter_tab_scheduled": "Reinícios Agendados",
                "restarter_chk_auto_restart": "Reiniciar servidor automaticamente ao detectar gatilho no log",
                "tooltip_restarter_chk_auto_restart": "Se marcado, o servidor será reiniciado após o gatilho de log ser detectado.",
                "restarter_lbl_trigger_msg": "Mensagem de Log para Gatilho de Reinício:",
                "tooltip_restarter_trigger_msg": "A linha de log (ou parte dela) que acionará o reinício do servidor.",
                "restarter_lbl_restart_delay": "Delay para Reiniciar após Gatilho (s):",
                "tooltip_restarter_restart_delay": "Tempo (s) para aguardar ANTES de iniciar o processo de reinício, após o gatilho ser detectado.",
                "restarter_scheduled_predefined": "Horários Pré-definidos (HH:00)",
                "restarter_scheduled_custom": "Horários Personalizados (HH:MM)",
                "restarter_scheduled_new": "Novo (HH:MM):",
                "tooltip_restarter_custom_time": "Digite o horário no formato HH:MM (ex: 08:30, 22:15)",
                "restarter_btn_add": "+ Adicionar", "restarter_btn_remove": "- Remover Selecionado",
                "tooltip_restarter_btn_remove": "Remove o horário personalizado selecionado na lista.",
                "dialog_invalid_time_format_title": "Formato Inválido",
                "dialog_invalid_time_format_msg": "Horário '{time}' inválido. Use o formato HH:MM.",
                "dialog_duplicate_time_title": "Horário Duplicado",
                "dialog_duplicate_time_msg": "O horário '{time}' já está na lista.",
                "dialog_no_selection_title": "Nenhuma Seleção",
                "dialog_no_selection_msg": "Selecione um horário para remover.",
                "log_scheduled_restart_triggered": "--- REINÍCIO AGENDADO ({time}) INICIADO ---",
                "log_trigger_detected": "Gatilho detectado. Aguardando {delay}s...",
                "log_error_no_service_for_restart": "ERRO: Nome do serviço não configurado para reinício ({type}).",
                "log_restart_process_started": "--- REINÍCIO {type} DO SERVIÇO '{service}' INICIADO ---",
                "dialog_server_restarted_title": "'{server}': Servidor Reiniciado",
                "dialog_server_restarted_msg": "O serviço '{service}' foi reiniciado com sucesso.",
                "dialog_restart_failed_title": "'{server}': Falha no Reinício",
                "dialog_restart_failed_msg": "Ocorreu um erro ao reiniciar o serviço '{service}'.",
                "log_restart_abort": "Falha ao parar '{service}'. Abortando reinício.",
                "log_wait_after_stop": "Aguardando {delay}s após a parada...",
                "log_wait_after_start": "Aguardando {delay}s após o início...", "restart_type_scheduled": "agendado",
                "restart_type_trigger": "por gatilho de log",
                "votemap_tab_paths_and_service": "Configuração de Caminhos e Serviço",
                "btn_select_server_json": "JSON Servidor",
                "tooltip_select_server_json": "Seleciona o arquivo JSON de configuração principal do servidor (ex: config.json).",
                "btn_select_votemap_json": "JSON Votemap",
                "tooltip_select_votemap_json": "Seleciona o arquivo JSON de configuração do Votemap (ex: votemap.json).",
                "lbl_server_json_prefix": "JSON Servidor", "lbl_votemap_json_prefix": "JSON Votemap",
                "btn_refresh_jsons": "Atualizar JSONs",
                "tooltip_btn_refresh_jsons": "Recarrega e exibe o conteúdo dos arquivos JSON selecionados.",
                "tab_json_server": "JSON Servidor", "tab_json_votemap": "JSON Votemap",
                "lbl_content_json_server": "CONTEÚDO DO JSON DO SERVIDOR",
                "lbl_content_json_votemap": "CONTEÚDO DO JSON DO VOTEMAP",
                "tab_votemap_options": "Opções Votemap",
                "votemap_chk_auto_restart": "Reiniciar servidor automaticamente após troca de mapa",
                "tooltip_votemap_chk_auto_restart": "Se marcado, o servidor será reiniciado após uma votação de mapa bem-sucedida.",
                "votemap_lbl_vote_pattern": "Padrão detecção de voto (RegEx):",
                "tooltip_votemap_vote_pattern": "Expressão regular para detectar o fim de uma votação no log.",
                "votemap_lbl_winner_pattern": "Padrão detecção de vencedor (RegEx):",
                "tooltip_votemap_winner_pattern": "Expressão regular para capturar o índice do mapa vencedor.",
                "votemap_lbl_default_mission": "Missão padrão de votemap (ScenarioID):",
                "tooltip_votemap_default_mission": "ID do cenário a ser carregado para iniciar uma nova votação.",
                "lbl_log_filename": "Nome do arquivo de log:",
                "tooltip_log_filename": "Nome do arquivo de log a ser monitorado (ex: console.log).",
                "lbl_stop_delay_short": "Delay Parar (s):", "lbl_start_delay_short": "Delay Iniciar (s):",
                "dialog_select_server_json_title": "Selecionar JSON de Config. do Servidor para '{server}'",
                "dialog_select_votemap_json_title": "Selecionar JSON de Votemap para '{server}'",
                "json_file_filter_name": "Arquivos JSON", "all_files_filter_name": "Todos",
                "log_warn_invalid_folder": "AVISO: Pasta de logs '{folder}' inválida.",
                "log_monitoring_file": "\n>>> Monitorando: {file}\n",
                "json_display_error": "ERRO: {error}", "json_decode_error": "ERRO ao decodificar JSON: {error}",
                "json_display_not_found": "Arquivo não encontrado.", "json_display_not_configured": "Não configurado.",
                "dialog_unsupported_os_votemap": "Gerenciamento de serviços não suportado no {os}.",
                "log_regex_error": "ERRO DE REGEX: {error}",
                "log_error_jsons_not_configured": "ERRO: JSONs de servidor ou votemap não configurados.",
                "log_warn_empty_map_list": "AVISO: Lista de mapas vazia.",
                "log_random_vote": "VOTO ALEATÓRIO: '{map}'.", "log_winner_map": "MAPA VENCEDOR: '{map}'.",
                "log_error_invalid_winner_index": "ERRO: Índice do vencedor ({index}) inválido.",
                "log_server_json_updated": "JSON do servidor atualizado para: {map}",
                "log_auto_restart_starting": "Iniciando reinício automático...",
                "log_error_map_change": "ERRO ao processar troca: {error}",
                "log_error_service_not_configured": "ERRO: Serviço não configurado.",
                "dialog_restart_complete_title": "'{server}': Reinício Concluído",
                "dialog_restart_complete_msg": "Serviço {service} reiniciado.",
                "dialog_restart_failed_votemap_title": "'{server}': Falha no Reinício",
                "dialog_restart_failed_votemap_msg": "Falha ao reiniciar {service}.",
                "log_restoring_json": "Restaurando JSON para votemap...",
                "log_warn_json_not_restored": "AVISO: JSON não restaurado (config incompleta).",
                "log_json_restored": "JSON restaurado.",
                "log_error_restoring_json": "ERRO ao restaurar JSON: {error}", "ok": "OK",
                # NOVO: Traduções para o sistema de notificação
                "notification_center_title": "Central de Notificações",
                "clear_notifications": "Limpar Histórico",
                "no_notifications": "Nenhuma notificação.",
                "closing_in": " (Fechando em {s}s)",
                "notification_cleared": "Histórico de notificações limpo.",
                "col_time": "Horário",
                "col_type": "Tipo",
                "col_title": "Título",
                "col_message": "Mensagem",
            },
            'en-us': {
                # Main App & Menus
                "app_title": "PQDT_Raphael - ArmaServerToolbox", "menu_language": "Language", "menu_file": "File",
                "menu_save_config": "Save Configuration", "menu_exit": "Exit", "menu_restarter": "Auto-Restarter",
                "menu_add_server": "Add Server", "menu_rename_server": "Rename Server",
                "menu_remove_current_server": "Remove Current Server", "menu_votemap": "Votemap Bypass",
                "menu_tools": "Tools", "menu_change_theme": "Change Theme", "menu_collect_player_info": "Collect Player Info", "menu_help": "Help", "menu_about": "About",
                "tab_top_restarter": "Auto-Restarter", "tab_top_votemap": "Votemap Bypass",
                "tab_system_log": "System Log",
                "status_ready": "Ready.", "status_config_saved": "Configuration saved!",
                "status_service_selected": "Service '{service}' selected for '{server}'.",
                "status_server_removed": "Server '{server}' ({tool}) removed.",
                "status_server_renamed": "Server renamed to '{name}'.",
                "dialog_rename_server_title": "Rename '{server}'",
                "dialog_rename_server_prompt": "Enter the new name for the server:",
                "dialog_rename_error_empty_title": "Invalid Name",
                "dialog_rename_error_empty_msg": "The server name cannot be empty.",
                "dialog_rename_error_duplicate_title": "Duplicate Name",
                "dialog_rename_error_duplicate_msg": "The name '{name}' is already in use in this tool.",
                "about_title": "Sobre / About",
                "about_message": (
                    "Esta é uma aplicação unificada que combina as funcionalidades do Auto-Restarter e do Votemap Bypass.\n\n"
                    "Use as abas superiores para alternar entre as ferramentas.\n"
                    "Cada ferramenta pode gerenciar múltiplos servidores em suas próprias abas internas.\n\n"
                    "Desenvolvido por PQDT_Raphael para a comunidade Predadores Brasil e KOTH Reforged."
                    "\n\n---\n\n"
                    "This is a unified application that combines the features of the Auto-Restarter and the Votemap Bypass.\n\n"
                    "Use the top tabs to switch between tools.\n"
                    "Each tool can manage multiple servers in its own internal tabs.\n\n"
                    "Developed by PQDT_Raphael for Predadores Brasil and KOTH Reforged community."
                ),
                "default_server_name": "Server {count}", "btn_select_log_folder": "Logs Folder",
                "tooltip_select_log_folder": "Selects the root folder where server logs are stored.",
                "btn_select_service": "Select Service",
                "tooltip_select_service": "Selects the service associated with the server (Windows or Linux).",
                "btn_start_service": "▶ Start Service", "tooltip_start_service": "Tries to start the selected service.",
                "btn_stop_service": "■ Stop Service", "tooltip_stop_service": "Tries to stop the selected service.",
                "btn_refresh_status": "↻", "tooltip_refresh_status": "Refresh status of the selected service.",
                "lbl_log_folder_prefix": "Logs Folder", "lbl_service_prefix": "Service", "status_none": "None",
                "status_invalid": "INVALID", "status_not_found_short": "NOT FND.",
                "status_not_found_long": "(Not found!)",
                "status_checking": "(Checking...)", "status_running_win": "(Running)",
                "status_stopped_win": "(Stopped)",
                "status_starting_win": "(Starting...)", "status_stopping_win": "(Stopping...)",
                "status_error": "(Error!)",
                "status_unknown": "(Unknown)", "status_active_linux": "(Active)", "status_inactive_linux": "(Inactive)",
                "status_failed_linux": "(Failed)", "status_activating_linux": "(Activating...)",
                "status_deactivating_linux": "(Deactivating...)",
                "na_pywin32": "N/A (pywin32)", "na_systemctl": "N/A (systemctl)", "na_os": "N/A (OS {os})",
                "lbl_log_controls": "Log Controls", "lbl_filter": "Filter:",
                "tooltip_filter": "Filters new log lines (case-insensitive).",
                "btn_pause": "⏸️ Pause", "btn_resume": "▶️ Resume",
                "tooltip_pause_resume": "Pauses or resumes live log monitoring.",
                "btn_clear_log": "♻️ Clear", "tooltip_clear_log": "Clears the server log display area.",
                "btn_restart_monitor": "↻ Mon.",
                "tooltip_restart_monitor": "Forces a restart of this tab's log monitor.",
                "lbl_server_logs": "Server Logs", "lbl_live_log": "LIVE SERVER LOG", "lbl_search": "Search:",
                "btn_next": "Next", "btn_previous": "Previous", "btn_close_search": "X",
                "chk_auto_scroll": "Auto-scroll",
                "chk_system_log_auto_scroll": "Auto-scroll", "lbl_stop_delay": "Stop Service Delay (s):",
                "tooltip_stop_delay_win": "Time (s) to wait after the service stop command.",
                "lbl_start_delay": "Start Service Delay (s):",
                "tooltip_start_delay_win": "Time (s) to wait for the service to fully start.",
                "dialog_select_folder_title": "Select the logs folder for '{server}'",
                "dialog_unsupported_os_title": "Unsupported",
                "dialog_unsupported_os_msg": "Service management is not supported on {os}.",
                "dialog_remove_server_title": "Remove '{server}'?",
                "dialog_remove_server_msg": "Are you sure you want to remove the server '{server}' from the {tool}?",
                "dialog_invalid_action_title": "Invalid Action",
                "dialog_invalid_action_msg": "Select a server tab to perform this action.",
                "dialog_theme_error_title": "Theme Error", "dialog_theme_error_msg": "Could not apply theme '{theme}'.",
                "dialog_save_error_title": "Error Saving", "dialog_save_error_msg": "Error: {error}",
                "warn_no_service_selected_title": "No Service Selected",
                "warn_no_service_to_stop": "Select a service to stop.",
                "warn_no_service_to_start": "Select a service to start.",
                "info_service_stopped_title": "Service Stopped",
                "info_service_stopped_msg": "The service '{service}' has been stopped.",
                "error_service_stop_failed_title": "Failed to Stop",
                "error_service_stop_failed_msg": "Could not stop service '{service}'. Check the logs.",
                "info_service_started_title": "Service Started",
                "info_service_started_msg": "The service '{service}' has been started.",
                "error_service_start_failed_title": "Failed to Start",
                "error_service_start_failed_msg": "Could not start service '{service}'. Check the logs.",
                "log_manual_stop": "--- MANUALLY STOPPING SERVICE '{service}' ---",
                "log_manual_start": "--- MANUALLY STARTING SERVICE '{service}' ---",
                "log_executing_sc_stop": "Executing 'sc stop {service}'...",
                "log_executing_sysd_stop": "Executing 'systemctl stop {service}'...",
                "log_unsupported_os_control": "ERROR: Operating system '{os}' not supported for service control.",
                "log_stop_cmd_sent": "Stop command for '{service}' sent successfully.",
                "log_stop_error": "ERROR stopping service '{service}': {error}",
                "log_executing_sc_start": "Executing 'sc start {service}'...",
                "log_executing_sysd_start": "Executing 'systemctl start {service}'...",
                "log_start_cmd_sent": "Start command for '{service}' sent successfully.",
                "log_start_error": "ERROR starting service '{service}': {error}",
                "dialog_missing_component_title": "Missing Component",
                "dialog_missing_pywin32": "pywin32 is required to list Windows services.",
                "dialog_missing_systemctl": "systemctl is required to list Linux services.",
                "dialog_loading_services_title": "Loading Services ({os})",
                "dialog_loading_services_msg": "Please wait...", "dialog_wmi_error_title": "WMI Error",
                "dialog_wmi_error_msg": "Failed to list services: {error}",
                "dialog_systemctl_error_title": "systemctl Error",
                "dialog_systemctl_error_msg": "Failed to list services: {error}",
                "dialog_no_services_found_title": "No Services Found",
                "dialog_no_services_found_msg": "No manageable services found for {os}.",
                "dialog_select_service_title": "Select Service for '{server}'",
                "dialog_service_name_header": "Service Name ({os})", "btn_confirm": "Confirm", "btn_cancel": "Cancel",
                "restarter_tab_paths_and_service": "Paths and Service Configuration",
                "restarter_tab_options": "Restart Options (Trigger)",
                "restarter_tab_scheduled": "Scheduled Restarts",
                "restarter_chk_auto_restart": "Automatically restart server on log trigger detection",
                "tooltip_restarter_chk_auto_restart": "If checked, the server will be restarted after the log trigger is detected.",
                "restarter_lbl_trigger_msg": "Log Message for Restart Trigger:",
                "tooltip_restarter_trigger_msg": "The log line (or part of it) that will trigger the server restart.",
                "restarter_lbl_restart_delay": "Delay to Restart After Trigger (s):",
                "tooltip_restarter_restart_delay": "Time (s) to wait BEFORE starting the restart process, after the trigger is detected.",
                "restarter_scheduled_predefined": "Predefined Times (HH:00)",
                "restarter_scheduled_custom": "Custom Times (HH:MM)",
                "restarter_scheduled_new": "New (HH:MM):",
                "tooltip_restarter_custom_time": "Enter the time in HH:MM format (e.g., 08:30, 22:15)",
                "restarter_btn_add": "+ Add", "restarter_btn_remove": "- Remove Selected",
                "tooltip_restarter_btn_remove": "Removes the selected custom time from the list.",
                "dialog_invalid_time_format_title": "Invalid Format",
                "dialog_invalid_time_format_msg": "Time '{time}' is invalid. Use HH:MM format.",
                "dialog_duplicate_time_title": "Duplicate Time",
                "dialog_duplicate_time_msg": "The time '{time}' is already in the list.",
                "dialog_no_selection_title": "No Selection", "dialog_no_selection_msg": "Select a time to remove.",
                "log_scheduled_restart_triggered": "--- SCHEDULED RESTART ({time}) INITIATED ---",
                "log_trigger_detected": "Trigger detected. Waiting {delay}s...",
                "log_error_no_service_for_restart": "ERROR: Service name not configured for {type} restart.",
                "log_restart_process_started": "--- {type} RESTART OF SERVICE '{service}' INITIATED ---",
                "dialog_server_restarted_title": "'{server}': Server Restarted",
                "dialog_server_restarted_msg": "The service '{service}' was restarted successfully.",
                "dialog_restart_failed_title": "'{server}': Restart Failed",
                "dialog_restart_failed_msg": "An error occurred while restarting service '{service}'.",
                "log_restart_abort": "Failed to stop '{service}'. Aborting restart.",
                "log_wait_after_stop": "Waiting {delay}s after stop...",
                "log_wait_after_start": "Waiting {delay}s after start...", "restart_type_scheduled": "scheduled",
                "restart_type_trigger": "by log trigger",
                "votemap_tab_paths_and_service": "Paths and Service Configuration",
                "btn_select_server_json": "Server JSON",
                "tooltip_select_server_json": "Selects the main server configuration JSON file (e.g., config.json).",
                "btn_select_votemap_json": "Votemap JSON",
                "tooltip_select_votemap_json": "Selects the Votemap configuration JSON file (e.g., votemap.json).",
                "lbl_server_json_prefix": "Server JSON", "lbl_votemap_json_prefix": "Votemap JSON",
                "btn_refresh_jsons": "Refresh JSONs",
                "tooltip_btn_refresh_jsons": "Reloads and displays the content of the selected JSON files.",
                "tab_json_server": "Server JSON", "tab_json_votemap": "Votemap JSON",
                "lbl_content_json_server": "SERVER JSON CONTENT", "lbl_content_json_votemap": "VOTEMAP JSON CONTENT",
                "tab_votemap_options": "Votemap Options",
                "votemap_chk_auto_restart": "Automatically restart server after map change",
                "tooltip_votemap_chk_auto_restart": "If checked, the server will be restarted after a successful map vote.",
                "votemap_lbl_vote_pattern": "Vote detection pattern (RegEx):",
                "tooltip_votemap_vote_pattern": "Regular expression to detect the end of a vote in the log.",
                "votemap_lbl_winner_pattern": "Winner detection pattern (RegEx):",
                "tooltip_votemap_winner_pattern": "Regular expression to capture the index of the winning map.",
                "votemap_lbl_default_mission": "Default votemap mission (ScenarioID):",
                "tooltip_votemap_default_mission": "ID of the scenario to be loaded to start a new vote.",
                "lbl_log_filename": "Log filename:",
                "tooltip_log_filename": "Name of the log file to monitor (e.g., console.log).",
                "lbl_stop_delay_short": "Stop Delay (s):", "lbl_start_delay_short": "Start Delay (s):",
                "dialog_select_server_json_title": "Select Server Config JSON for '{server}'",
                "dialog_select_votemap_json_title": "Select Votemap JSON for '{server}'",
                "json_file_filter_name": "JSON Files", "all_files_filter_name": "All Files",
                "log_warn_invalid_folder": "WARNING: Log folder '{folder}' is invalid.",
                "log_monitoring_file": "\n>>> Monitoring: {file}\n",
                "json_display_error": "ERROR: {error}", "json_decode_error": "ERROR decoding JSON: {error}",
                "json_display_not_found": "File not found.", "json_display_not_configured": "Not configured.",
                "dialog_unsupported_os_votemap": "Service management is not supported on {os}.",
                "log_regex_error": "REGEX ERROR: {error}",
                "log_error_jsons_not_configured": "ERROR: Server or votemap JSONs not configured.",
                "log_warn_empty_map_list": "WARNING: Map list is empty.",
                "log_random_vote": "RANDOM VOTE: '{map}'.", "log_winner_map": "WINNING MAP: '{map}'.",
                "log_error_invalid_winner_index": "ERROR: Winner index ({index}) is invalid.",
                "log_server_json_updated": "Server JSON updated to: {map}",
                "log_auto_restart_starting": "Starting automatic restart...",
                "log_error_map_change": "ERROR processing map change: {error}",
                "log_error_service_not_configured": "ERROR: Service not configured.",
                "dialog_restart_complete_title": "'{server}': Restart Complete",
                "dialog_restart_complete_msg": "Service {service} has been restarted.",
                "dialog_restart_failed_votemap_title": "'{server}': Restart Failed",
                "dialog_restart_failed_votemap_msg": "Failed to restart {service}.",
                "log_restoring_json": "Restoring JSON to votemap...",
                "log_warn_json_not_restored": "WARNING: JSON not restored (incomplete config).",
                "log_json_restored": "JSON restored.",
                "log_error_restoring_json": "ERROR restoring JSON: {error}", "ok": "OK",
                # NEW: Notification system translations
                "notification_center_title": "Notification Center",
                "clear_notifications": "Clear History",
                "no_notifications": "No notifications.",
                "closing_in": " (Closing in {s}s)",
                "notification_cleared": "Notification history cleared.",
                "col_time": "Time",
                "col_type": "Type",
                "col_title": "Title",
                "col_message": "Message",
            }
        }


# ==============================================================================
# CLASSE NotificationToast - NOVA CLASSE PARA NOTIFICAÇÕES
# ==============================================================================
class NotificationToast(ttk.Toplevel):
    def __init__(self, master_app, title, message, boxtype='info', duration=5):
        super().__init__(master_app.root)
        self.app = master_app
        self.duration = duration
        self.boxtype = boxtype

        # Remove a barra de título
        self.overrideredirect(True)

        # Mapeia o tipo para uma cor do bootstrap
        color_map = {'info': 'info', 'success': 'success', 'warning': 'warning', 'error': 'danger'}
        style_color = color_map.get(boxtype, 'secondary')

        # Frame principal com borda colorida
        self.container = ttk.Frame(self, bootstyle=f'{style_color}', padding=1)
        self.container.pack(expand=True, fill='both')

        inner_frame = ttk.Frame(self.container, padding=(10, 5))
        inner_frame.pack(expand=True, fill='both')

        # Título da Notificação
        title_label = ttk.Label(inner_frame, text=title, font=("-weight bold",))
        title_label.pack(side='top', fill='x')

        ttk.Separator(inner_frame).pack(side='top', fill='x', pady=5)

        # Mensagem da Notificação
        msg_label = ttk.Label(inner_frame, text=message, wraplength=380)
        msg_label.pack(side='top', fill='x', pady=(0, 5))

        # Label para a contagem regressiva
        self.countdown_label_var = tk.StringVar()
        countdown_label = ttk.Label(inner_frame, textvariable=self.countdown_label_var, font=("-size 7",))
        countdown_label.pack(side='bottom', fill='x', anchor='e')

        self.update_idletasks()
        self.countdown(self.duration)

    def countdown(self, seconds_left):
        _ = self.app.translator.get
        if seconds_left > 0:
            self.countdown_label_var.set(_('closing_in', s=seconds_left))
            self.after_id = self.after(1000, lambda: self.countdown(seconds_left - 1))
        else:
            self.close_toast()

    def close_toast(self):
        if hasattr(self, 'after_id'):
            self.after_cancel(self.after_id)
        self.app.on_toast_closed(self)
        self.destroy()


# ==============================================================================
# CLASSE RestarterTab (Originalmente ServidorTab de PQD_ScheduledRestart.PY)
# ==============================================================================
class RestarterTab(ttk.Frame):
    def __init__(self, master_notebook, app_instance, nome_servidor, config_dict=None):
        super().__init__(master_notebook)
        self.app = app_instance
        self.nome = nome_servidor
        self.config_inicial = config_dict if config_dict else {}
        self.logger = restarter_logger  # Usa o logger específico

        # --- Variáveis de Estado (tk.Variables) ---
        self.pasta_raiz = tk.StringVar(value=self.config_inicial.get("log_folder", ""))
        self.nome_servico = tk.StringVar(value=self.config_inicial.get("service_name", ""))
        self.log_filename_var = tk.StringVar(value=self.config_inicial.get("log_filename", "console.log"))
        self.trigger_log_message_var = tk.StringVar(
            value=self.config_inicial.get("trigger_log_message", "ServerAdminTools | Event serveradmintools_game_ended")
        )
        self.restart_delay_after_trigger_var = tk.IntVar(
            value=self.config_inicial.get("restart_delay_after_trigger", 10)
        )
        self.auto_restart_on_trigger_var = tk.BooleanVar(
            value=self.config_inicial.get("auto_restart_on_trigger", True)
        )
        self.log_folder_path_label_var = tk.StringVar()
        self.servico_label_var = tk.StringVar()
        self.filtro_var = tk.StringVar(value=self.config_inicial.get("filter", ""))
        self.stop_delay_var = tk.IntVar(value=self.config_inicial.get("stop_delay", 10))
        self.start_delay_var = tk.IntVar(value=self.config_inicial.get("start_delay", 30))
        self.auto_scroll_log_var = tk.BooleanVar(value=self.config_inicial.get("auto_scroll_log", True))
        self.log_search_var = tk.StringVar()
        self.scheduled_restarts_list = list(self.config_inicial.get("scheduled_restarts", []))
        self.predefined_schedule_vars = {}
        self.custom_schedule_entry_var = tk.StringVar()
        self.last_scheduled_restart_processed_time_str = None
        self.last_search_pos = "1.0"
        self.search_log_frame_visible = False

        # --- Threads e Eventos ---
        self._stop_event = threading.Event()
        self._scheduler_stop_event = threading.Event()
        self._paused = False
        self.log_monitor_thread = None
        self.scheduler_thread = None

        self._create_ui_for_tab()
        self.update_ui_text()
        self.initialize_from_config_vars()
        self._update_scheduled_restarts_ui_from_list()

        vars_to_trace = [
            self.pasta_raiz, self.nome_servico, self.filtro_var, self.log_filename_var,
            self.trigger_log_message_var, self.auto_restart_on_trigger_var,
            self.auto_scroll_log_var, self.stop_delay_var, self.start_delay_var,
            self.restart_delay_after_trigger_var
        ]
        for var in vars_to_trace:
            var.trace_add("write", lambda *args, v=var: self._value_changed())

        self.start_scheduler_thread()

    def _value_changed(self, new_value=None):
        self.app.mark_config_changed()

    def get_current_config(self):
        return {
            "nome": self.nome,
            "log_folder": self.pasta_raiz.get(),
            "service_name": self.nome_servico.get(),
            "log_filename": self.log_filename_var.get(),
            "filter": self.filtro_var.get(),
            "auto_restart_on_trigger": self.auto_restart_on_trigger_var.get(),
            "trigger_log_message": self.trigger_log_message_var.get(),
            "restart_delay_after_trigger": self.restart_delay_after_trigger_var.get(),
            "stop_delay": self.stop_delay_var.get(),
            "start_delay": self.start_delay_var.get(),
            "auto_scroll_log": self.auto_scroll_log_var.get(),
            "scheduled_restarts": sorted(list(set(self.scheduled_restarts_list)))
        }

    def _create_ui_for_tab(self):
        outer_top_frame = ttk.Frame(self)
        outer_top_frame.pack(pady=5, padx=5, fill='x')

        self.selection_labelframe = ttk.Labelframe(outer_top_frame, padding=(10, 5))
        self.selection_labelframe.pack(side='top', fill='x', pady=(0, 5))

        path_buttons_frame = ttk.Frame(self.selection_labelframe)
        path_buttons_frame.pack(fill='x')

        self.selecionar_btn = ttk.Button(path_buttons_frame, command=self.selecionar_pasta, bootstyle=PRIMARY)
        self.selecionar_btn.pack(side='left', pady=2, padx=(0, 2))
        self.selecionar_btn_tooltip = ToolTip(self.selecionar_btn)

        self.servico_btn = ttk.Button(path_buttons_frame, command=self.selecionar_servico, bootstyle=SECONDARY)
        self.servico_btn.pack(side='left', padx=2, pady=2)
        self.servico_btn_tooltip = ToolTip(self.servico_btn)

        self.iniciar_servico_btn = ttk.Button(path_buttons_frame, command=self.iniciar_servico_manual,
                                              bootstyle=SUCCESS)
        self.iniciar_servico_btn.pack(side='left', padx=(5, 2), pady=2)
        self.iniciar_servico_btn_tooltip = ToolTip(self.iniciar_servico_btn)

        self.parar_servico_btn = ttk.Button(path_buttons_frame, command=self.parar_servico_manual, bootstyle=DANGER)
        self.parar_servico_btn.pack(side='left', padx=2, pady=2)
        self.parar_servico_btn_tooltip = ToolTip(self.parar_servico_btn)

        self.refresh_servico_status_btn = ttk.Button(path_buttons_frame, command=self.update_service_status_display,
                                                     bootstyle=(TOOLBUTTON, LIGHT), width=2)
        self.refresh_servico_status_btn.pack(side='left', padx=(5, 2), pady=2)
        self.refresh_servico_status_btn_tooltip = ToolTip(self.refresh_servico_status_btn)

        path_labels_frame_line1 = ttk.Frame(self.selection_labelframe)
        path_labels_frame_line1.pack(fill='x', pady=(5, 2))
        self.log_folder_path_label = ttk.Label(path_labels_frame_line1, textvariable=self.log_folder_path_label_var,
                                               wraplength=450, anchor='w')
        self.log_folder_path_label.pack(side='left', padx=5, fill='x', expand=True)
        self.servico_label_widget = ttk.Label(path_labels_frame_line1, textvariable=self.servico_label_var, anchor='w',
                                              width=30)
        self.servico_label_widget.pack(side='left', padx=(5, 0))

        self.controls_labelframe = ttk.Labelframe(outer_top_frame, padding=(10, 5))
        self.controls_labelframe.pack(side='top', fill='x', pady=(5, 0))

        log_controls_subframe = ttk.Frame(self.controls_labelframe)
        log_controls_subframe.pack(fill='x', expand=True)

        self.filtro_lbl = ttk.Label(log_controls_subframe)
        self.filtro_lbl.pack(side='left', padx=(0, 5))
        self.filtro_entry = ttk.Entry(log_controls_subframe, textvariable=self.filtro_var, width=20)
        self.filtro_entry.pack(side='left', padx=(0, 5))
        self.filtro_entry_tooltip = ToolTip(self.filtro_entry)

        self.pausar_btn = ttk.Button(log_controls_subframe, command=self.toggle_pausa, bootstyle=WARNING)
        self.pausar_btn.pack(side='left', padx=5)
        self.pausar_btn_tooltip = ToolTip(self.pausar_btn)

        self.limpar_btn = ttk.Button(log_controls_subframe, command=self.limpar_tela_log, bootstyle=SECONDARY)
        self.limpar_btn.pack(side='left', padx=5)
        self.limpar_btn_tooltip = ToolTip(self.limpar_btn)

        self.restart_monitor_btn = ttk.Button(log_controls_subframe, command=self.restart_log_monitoring,
                                              bootstyle=(TOOLBUTTON, INFO))
        self.restart_monitor_btn.pack(side='left', padx=5)
        self.restart_monitor_btn_tooltip = ToolTip(self.restart_monitor_btn)

        self.tab_notebook = ttk.Notebook(self)
        self.tab_notebook.pack(fill='both', expand=True, padx=5, pady=(5, 5))

        self.log_frame = ttk.Frame(self.tab_notebook)
        self.tab_notebook.add(self.log_frame)
        self.log_label_display = ttk.Label(self.log_frame, foreground="red")
        self.log_label_display.pack(pady=(5, 0))

        self.search_log_frame = ttk.Frame(self.log_frame)
        self.search_lbl = ttk.Label(self.search_log_frame)
        self.search_lbl.pack(side='left', padx=(5, 2))
        self.log_search_entry = ttk.Entry(self.search_log_frame, textvariable=self.log_search_var)
        self.log_search_entry.pack(side='left', fill='x', expand=True, padx=2)
        self.log_search_entry.bind("<Return>", self._search_log_next)
        self.search_next_btn = ttk.Button(self.search_log_frame, command=self._search_log_next, bootstyle=SECONDARY)
        self.search_next_btn.pack(side='left', padx=2)
        self.search_prev_btn = ttk.Button(self.search_log_frame, command=self._search_log_prev, bootstyle=SECONDARY)
        self.search_prev_btn.pack(side='left', padx=2)
        self.close_search_btn = ttk.Button(self.search_log_frame, command=self._toggle_log_search_bar,
                                           bootstyle=(SECONDARY, DANGER), width=2)
        self.close_search_btn.pack(side='left', padx=(2, 5))

        self.text_area_log = ScrolledText(self.log_frame, wrap='word', height=10, state='disabled')
        self.text_area_log.pack(fill='both', expand=True, pady=(0, 5))
        self.text_area_log.bind("<Control-f>", lambda e: self._toggle_log_search_bar(force_show=True))

        self.auto_scroll_check = ttk.Checkbutton(self, variable=self.auto_scroll_log_var)
        self.auto_scroll_check.pack(in_=self.log_frame, side='left', anchor='sw', pady=2, padx=5)

        self.options_frame = ttk.Frame(self.tab_notebook)
        self.tab_notebook.add(self.options_frame)
        options_inner_frame = ttk.Frame(self.options_frame, padding=15)
        options_inner_frame.pack(fill='both', expand=True)

        self.auto_restart_check = ttk.Checkbutton(options_inner_frame, variable=self.auto_restart_on_trigger_var)
        self.auto_restart_check.grid(row=0, column=0, sticky='w', padx=5, pady=5, columnspan=2)
        self.auto_restart_check_tooltip = ToolTip(self.auto_restart_check)

        self.trigger_message_lbl = ttk.Label(options_inner_frame)
        self.trigger_message_lbl.grid(row=1, column=0, sticky='w', padx=5, pady=(10, 0))
        self.trigger_message_entry = ttk.Entry(options_inner_frame, textvariable=self.trigger_log_message_var, width=60)
        self.trigger_message_entry.grid(row=2, column=0, sticky='ew', padx=5, pady=2, columnspan=2)
        self.trigger_message_entry_tooltip = ToolTip(self.trigger_message_entry)

        self.restart_delay_lbl = ttk.Label(options_inner_frame)
        self.restart_delay_lbl.grid(row=3, column=0, sticky='w', padx=5, pady=(10, 0))
        self.restart_delay_spinbox = ttk.Spinbox(options_inner_frame, from_=0, to=300,
                                                 textvariable=self.restart_delay_after_trigger_var, width=5)
        self.restart_delay_spinbox.grid(row=4, column=0, sticky='w', padx=5, pady=2)
        self.restart_delay_spinbox_tooltip = ToolTip(self.restart_delay_spinbox)

        self.log_filename_lbl = ttk.Label(options_inner_frame)
        self.log_filename_lbl.grid(row=5, column=0, sticky='w', padx=5, pady=(10, 0))
        self.log_filename_entry = ttk.Entry(options_inner_frame, textvariable=self.log_filename_var, width=40)
        self.log_filename_entry.grid(row=6, column=0, sticky='ew', padx=5, pady=2, columnspan=2)
        self.log_filename_entry_tooltip = ToolTip(self.log_filename_entry)

        delay_frame = ttk.Frame(options_inner_frame)
        delay_frame.grid(row=7, column=0, columnspan=2, sticky='ew', pady=(20, 0))
        self.stop_delay_lbl = ttk.Label(delay_frame)
        self.stop_delay_lbl.pack(side='left', padx=5)
        self.stop_delay_spinbox = ttk.Spinbox(delay_frame, from_=1, to=60, textvariable=self.stop_delay_var, width=5)
        self.stop_delay_spinbox.pack(side='left', padx=5)
        self.stop_delay_spinbox_tooltip = ToolTip(self.stop_delay_spinbox)

        self.start_delay_lbl = ttk.Label(delay_frame)
        self.start_delay_lbl.pack(side='left', padx=15)
        self.start_delay_spinbox = ttk.Spinbox(delay_frame, from_=5, to=180, textvariable=self.start_delay_var, width=5)
        self.start_delay_spinbox.pack(side='left', padx=5)
        self.start_delay_spinbox_tooltip = ToolTip(self.start_delay_spinbox)
        options_inner_frame.columnconfigure(0, weight=1)

        self.scheduled_restarts_frame = ttk.Frame(self.tab_notebook, padding=10)
        self.tab_notebook.add(self.scheduled_restarts_frame)
        self._create_scheduled_restarts_ui(self.scheduled_restarts_frame)

    def update_ui_text(self):
        """Atualiza o texto de todos os widgets na aba com base no idioma atual."""
        _ = self.app.translator.get

        self.selection_labelframe.config(text=_('restarter_tab_paths_and_service'))
        self.selecionar_btn.config(text=_('btn_select_log_folder'))
        self.selecionar_btn_tooltip.text = _('tooltip_select_log_folder')
        self.servico_btn.config(text=_('btn_select_service'))
        self.servico_btn_tooltip.text = _('tooltip_select_service')
        self.iniciar_servico_btn.config(text=_('btn_start_service'))
        self.iniciar_servico_btn_tooltip.text = _('tooltip_start_service')
        self.parar_servico_btn.config(text=_('btn_stop_service'))
        self.parar_servico_btn_tooltip.text = _('tooltip_stop_service')
        self.refresh_servico_status_btn.config(text=_('btn_refresh_status'))
        self.refresh_servico_status_btn_tooltip.text = _('tooltip_refresh_status')

        self.controls_labelframe.config(text=_('lbl_log_controls'))
        self.filtro_lbl.config(text=_('lbl_filter'))
        self.filtro_entry_tooltip.text = _('tooltip_filter')
        self.pausar_btn.config(text=_('btn_resume') if self._paused else _('btn_pause'))
        self.pausar_btn_tooltip.text = _('tooltip_pause_resume')
        self.limpar_btn.config(text=_('btn_clear_log'))
        self.limpar_btn_tooltip.text = _('tooltip_clear_log')
        self.restart_monitor_btn.config(text=_('btn_restart_monitor'))
        self.restart_monitor_btn_tooltip.text = _('tooltip_restart_monitor')

        self.tab_notebook.tab(self.log_frame, text=_('lbl_server_logs'))
        self.log_label_display.config(text=_('lbl_live_log'))
        self.search_lbl.config(text=_('lbl_search'))
        self.search_next_btn.config(text=_('btn_next'))
        self.search_prev_btn.config(text=_('btn_previous'))
        self.close_search_btn.config(text=_('btn_close_search'))
        self.auto_scroll_check.config(text=_('chk_auto_scroll'))

        self.tab_notebook.tab(self.options_frame, text=_('restarter_tab_options'))
        self.auto_restart_check.config(text=_('restarter_chk_auto_restart'))
        self.auto_restart_check_tooltip.text = _('tooltip_restarter_chk_auto_restart')
        self.trigger_message_lbl.config(text=_('restarter_lbl_trigger_msg'))
        self.trigger_message_entry_tooltip.text = _('tooltip_restarter_trigger_msg')
        self.restart_delay_lbl.config(text=_('restarter_lbl_restart_delay'))
        self.restart_delay_spinbox_tooltip.text = _('tooltip_restarter_restart_delay')
        self.log_filename_lbl.config(text=_('lbl_log_filename'))
        self.log_filename_entry_tooltip.text = _('tooltip_log_filename')
        self.stop_delay_lbl.config(text=_('lbl_stop_delay'))
        self.stop_delay_spinbox_tooltip.text = _('tooltip_stop_delay_win')
        self.start_delay_lbl.config(text=_('lbl_start_delay'))
        self.start_delay_spinbox_tooltip.text = _('tooltip_start_delay_win')

        self.tab_notebook.tab(self.scheduled_restarts_frame, text=_('restarter_tab_scheduled'))
        self.predefined_lf.config(text=_('restarter_scheduled_predefined'))
        self.custom_lf.config(text=_('restarter_scheduled_custom'))
        self.custom_add_lbl.config(text=_('restarter_scheduled_new'))
        self.custom_entry_tooltip.text = _('tooltip_restarter_custom_time')
        self.add_btn.config(text=_('restarter_btn_add'))
        self.remove_btn.config(text=_('restarter_btn_remove'))
        self.remove_btn_tooltip.text = _('tooltip_restarter_btn_remove')

        # Atualiza labels dinâmicas que dependem de estado
        self.initialize_from_config_vars()

    def _create_scheduled_restarts_ui(self, parent_frame):
        # Cria widgets
        self.predefined_lf = ttk.Labelframe(parent_frame, padding=10)
        self.predefined_lf.pack(fill="x", pady=5)
        predefined_grid_frame = ttk.Frame(self.predefined_lf)
        predefined_grid_frame.pack(fill="x")
        cols = 6
        for i in range(24):
            hour_str = f"{i:02d}:00"
            var = tk.BooleanVar(value=(hour_str in self.scheduled_restarts_list))
            cb = ttk.Checkbutton(predefined_grid_frame, text=hour_str, variable=var,
                                 command=lambda h=i, v=var: self._toggle_predefined_schedule(h, v))
            cb.grid(row=i // cols, column=i % cols, padx=5, pady=2, sticky="w")
            self.predefined_schedule_vars[hour_str] = var

        self.custom_lf = ttk.Labelframe(parent_frame, padding=10)
        self.custom_lf.pack(fill="both", expand=True, pady=5)
        custom_add_frame = ttk.Frame(self.custom_lf)
        custom_add_frame.pack(fill="x", pady=(0, 5))
        self.custom_add_lbl = ttk.Label(custom_add_frame)
        self.custom_add_lbl.pack(side="left", padx=(0, 5))
        custom_entry = ttk.Entry(custom_add_frame, textvariable=self.custom_schedule_entry_var, width=10)
        custom_entry.pack(side="left", padx=5)
        self.custom_entry_tooltip = ToolTip(custom_entry)
        self.add_btn = ttk.Button(custom_add_frame, command=self._add_custom_schedule, bootstyle=SUCCESS)
        self.add_btn.pack(side="left", padx=5)

        custom_list_remove_frame = ttk.Frame(self.custom_lf)
        custom_list_remove_frame.pack(fill="both", expand=True)
        self.custom_schedules_listbox = tk.Listbox(custom_list_remove_frame, selectmode=tk.SINGLE, height=6)
        self.custom_schedules_listbox.pack(side="left", fill="both", expand=True, padx=(0, 5))
        custom_scroll = ttk.Scrollbar(custom_list_remove_frame, orient="vertical",
                                      command=self.custom_schedules_listbox.yview)
        custom_scroll.pack(side="left", fill="y")
        self.custom_schedules_listbox.config(yscrollcommand=custom_scroll.set)
        self.remove_btn = ttk.Button(custom_list_remove_frame, command=self._remove_selected_custom_schedule,
                                     bootstyle=DANGER)
        self.remove_btn.pack(side="left", padx=(5, 0), anchor="n")
        self.remove_btn_tooltip = ToolTip(self.remove_btn)

    def _update_scheduled_restarts_ui_from_list(self):
        if not hasattr(self, 'predefined_schedule_vars') or not hasattr(self, 'custom_schedules_listbox'):
            return

        for hour_str, var in self.predefined_schedule_vars.items():
            if var.get() != (hour_str in self.scheduled_restarts_list):
                var.set(hour_str in self.scheduled_restarts_list)

        if self.custom_schedules_listbox.winfo_exists():
            self.custom_schedules_listbox.delete(0, tk.END)
            all_times = set(self.scheduled_restarts_list)
            predefined_as_set = {f"{h:02d}:00" for h in range(24)}
            actually_custom_times = sorted(list(all_times - predefined_as_set))
            for time_str in actually_custom_times:
                self.custom_schedules_listbox.insert(tk.END, time_str)

    def _toggle_predefined_schedule(self, hour_int, var):
        hour_str = f"{hour_int:02d}:00"
        if var.get():
            if hour_str not in self.scheduled_restarts_list:
                self.scheduled_restarts_list.append(hour_str)
        else:
            if hour_str in self.scheduled_restarts_list:
                self.scheduled_restarts_list.remove(hour_str)
        self.scheduled_restarts_list = sorted(list(set(self.scheduled_restarts_list)))
        self._value_changed()

    def _add_custom_schedule(self):
        time_str = self.custom_schedule_entry_var.get().strip()
        if not re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", time_str):
            self.app.show_messagebox_from_thread("error",
                                                 self.app.translator.get("dialog_invalid_time_format_title"),
                                                 self.app.translator.get("dialog_invalid_time_format_msg",
                                                                         time=time_str))
            return
        if time_str in self.scheduled_restarts_list:
            self.app.show_messagebox_from_thread("info",
                                                 self.app.translator.get("dialog_duplicate_time_title"),
                                                 self.app.translator.get("dialog_duplicate_time_msg", time=time_str))
            return
        self.scheduled_restarts_list.append(time_str)
        self.scheduled_restarts_list = sorted(list(set(self.scheduled_restarts_list)))
        self._update_scheduled_restarts_ui_from_list()
        self.custom_schedule_entry_var.set("")
        self._value_changed()

    def _remove_selected_custom_schedule(self):
        selection_indices = self.custom_schedules_listbox.curselection()
        if not selection_indices:
            self.app.show_messagebox_from_thread("warning",
                                                 self.app.translator.get("dialog_no_selection_title"),
                                                 self.app.translator.get("dialog_no_selection_msg"))
            return
        selected_time_str = self.custom_schedules_listbox.get(selection_indices[0])
        if selected_time_str in self.scheduled_restarts_list:
            self.scheduled_restarts_list.remove(selected_time_str)
            self._update_scheduled_restarts_ui_from_list()
            self._value_changed()

    def start_scheduler_thread(self):
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            return
        self._scheduler_stop_event.clear()
        self.scheduler_thread = threading.Thread(target=self._scheduler_worker, daemon=True,
                                                 name=f"Scheduler-{self.nome}")
        self.scheduler_thread.start()
        self.logger.info(f"Tab '{self.nome}': Scheduler de reinícios agendados iniciado.")

    def stop_scheduler_thread(self, from_tab_closure=False):
        self._scheduler_stop_event.set()
        if self.scheduler_thread and self.scheduler_thread.is_alive() and self.scheduler_thread != threading.current_thread():
            self.scheduler_thread.join(timeout=2.0)
        self.scheduler_thread = None

    def _scheduler_worker(self):
        while not self._scheduler_stop_event.is_set():
            try:
                current_time_str_hh_mm = datetime.now().strftime("%H:%M")
                if self.last_scheduled_restart_processed_time_str != current_time_str_hh_mm:
                    self.last_scheduled_restart_processed_time_str = None

                service_to_restart = self.nome_servico.get()
                if not service_to_restart or not self.scheduled_restarts_list:
                    if self._scheduler_stop_event.wait(20): break
                    continue

                if (current_time_str_hh_mm in self.scheduled_restarts_list and
                        self.last_scheduled_restart_processed_time_str != current_time_str_hh_mm):
                    self.logger.info(
                        f"Tab '{self.nome}': Disparando reinício agendado para '{service_to_restart}' às {current_time_str_hh_mm}.")
                    self.append_text_to_log_area_threadsafe(
                        self.app.translator.get("log_scheduled_restart_triggered", time=current_time_str_hh_mm) + "\n")
                    threading.Thread(
                        target=self._executar_logica_reinicio_servico_efetivamente,
                        args=(True,), daemon=True, name=f"ScheduledRestartExec-{self.nome}"
                    ).start()
                    self.last_scheduled_restart_processed_time_str = current_time_str_hh_mm
            except Exception as e_scheduler:
                self.logger.error(f"Tab '{self.nome}': Erro no _scheduler_worker: {e_scheduler}", exc_info=True)

            if self._scheduler_stop_event.wait(15):
                break
        self.logger.info(f"Tab '{self.nome}': Thread _scheduler_worker encerrada.")

    def _update_manual_control_button_states(self):
        has_service = bool(self.nome_servico.get())
        os_system = platform.system()
        can_manage = (os_system == "Windows" and PYWIN32_AVAILABLE) or \
                     (os_system == "Linux" and SYSTEMCTL_AVAILABLE)
        new_state = NORMAL if has_service and can_manage else DISABLED
        if self.iniciar_servico_btn.winfo_exists(): self.iniciar_servico_btn.config(state=new_state)
        if self.parar_servico_btn.winfo_exists(): self.parar_servico_btn.config(state=new_state)

    def initialize_from_config_vars(self):
        _ = self.app.translator.get
        default_fg = "black"
        try:
            if hasattr(self.app.style, 'colors') and hasattr(self.app.style.colors, 'fg'):
                default_fg = self.app.style.colors.fg if self.app.style.colors.fg else "black"
        except Exception:
            pass

        pasta_raiz_val = self.pasta_raiz.get()
        log_folder_prefix = _('lbl_log_folder_prefix')
        if pasta_raiz_val and os.path.isdir(pasta_raiz_val):
            self.log_folder_path_label_var.set(f"{log_folder_prefix}: {os.path.basename(pasta_raiz_val)}")
            self.log_folder_path_label.config(foreground="green")
            self.start_log_monitoring()
        elif pasta_raiz_val:
            self.log_folder_path_label_var.set(
                f"{log_folder_prefix} ({_('status_invalid')}): {os.path.basename(pasta_raiz_val)}")
            self.log_folder_path_label.config(foreground="red")
        else:
            self.log_folder_path_label_var.set(f"{log_folder_prefix}: {_('status_none')}")
            self.log_folder_path_label.config(foreground=default_fg)

        os_system = platform.system()
        can_manage_services = (os_system == "Windows" and PYWIN32_AVAILABLE) or (
                os_system == "Linux" and SYSTEMCTL_AVAILABLE)
        if self.servico_btn.winfo_exists(): self.servico_btn.config(state=NORMAL if can_manage_services else DISABLED)

        nome_servico_val = self.nome_servico.get()
        can_refresh_status = bool(nome_servico_val) and can_manage_services
        if self.refresh_servico_status_btn.winfo_exists(): self.refresh_servico_status_btn.config(
            state=NORMAL if can_refresh_status else DISABLED)

        service_prefix = _('lbl_service_prefix')
        if nome_servico_val:
            self.update_service_status_display()
        else:
            service_unavailable_reason = ""
            if not can_manage_services:
                if os_system == "Windows":
                    service_unavailable_reason = _('na_pywin32')
                elif os_system == "Linux":
                    service_unavailable_reason = _('na_systemctl')
                else:
                    service_unavailable_reason = _('na_os', os=os_system)
            if service_unavailable_reason:
                self.servico_label_var.set(f"{service_prefix}: {service_unavailable_reason}")
                self.servico_label_widget.config(foreground="gray")
            else:
                self.servico_label_var.set(f"{service_prefix}: {_('status_none')}")
                self.servico_label_widget.config(foreground="orange")

        self._update_manual_control_button_states()
        self._update_scheduled_restarts_ui_from_list()
        self.start_scheduler_thread()

    def selecionar_pasta(self):
        pasta_selecionada = filedialog.askdirectory(
            title=self.app.translator.get("dialog_select_folder_title", server=self.nome))
        if pasta_selecionada and self.pasta_raiz.get() != pasta_selecionada:
            self.stop_log_monitoring()
            self.pasta_raiz.set(pasta_selecionada)
            self.initialize_from_config_vars()

    def selecionar_servico(self):
        os_system = platform.system()
        if os_system == "Windows":
            self.app.iniciar_selecao_servico_para_aba(self, "windows")
        elif os_system == "Linux":
            self.app.iniciar_selecao_servico_para_aba(self, "linux")
        else:
            self.app.show_messagebox_from_thread("warning", self.app.translator.get("dialog_unsupported_os_title"),
                                                 self.app.translator.get("dialog_unsupported_os_msg", os=os_system))

    def set_selected_service(self, service_name):
        if self.nome_servico.get() != service_name:
            self.nome_servico.set(service_name)
            self.update_service_status_display()
            self.app.set_status_from_thread(
                self.app.translator.get("status_service_selected", service=service_name, server=self.nome))
            self.logger.info(f"Tab '{self.nome}': Serviço selecionado: {service_name}")
        self._update_manual_control_button_states()

    def update_service_status_display(self):
        nome_servico_val = self.nome_servico.get()
        if not nome_servico_val:
            self.initialize_from_config_vars()
            return
        os_system = platform.system()
        worker = None
        if os_system == "Windows":
            if not PYWIN32_AVAILABLE: self.initialize_from_config_vars(); return
            worker = self._get_and_display_service_status_win_thread_worker
        elif os_system == "Linux":
            if not SYSTEMCTL_AVAILABLE: self.initialize_from_config_vars(); return
            worker = self._get_and_display_service_status_linux_thread_worker
        else:
            self.initialize_from_config_vars();
            return

        _ = self.app.translator.get
        current_text_base = f"{_('lbl_service_prefix')}: {nome_servico_val}"
        self.servico_label_var.set(f"{current_text_base} ({_('status_checking')})")
        self.servico_label_widget.config(foreground="blue")
        threading.Thread(
            target=worker, args=(nome_servico_val, current_text_base), daemon=True,
            name=f"ServiceStatusCheck-{self.nome}"
        ).start()

    def _get_and_display_service_status_win_thread_worker(self, service_name, base_text):
        status = self._verificar_status_servico_win(service_name)
        _ = self.app.translator.get
        status_map = {
            "RUNNING": (_('status_running_win'), "green"), "STOPPED": (_('status_stopped_win'), "red"),
            "START_PENDING": (_('status_starting_win'), "blue"), "STOP_PENDING": (_('status_stopping_win'), "blue"),
            "NOT_FOUND": (_('status_not_found_long'), "orange"), "ERROR": (_('status_error'), "red"),
            "UNKNOWN": (_('status_unknown'), "gray")
        }
        display_text, color = status_map.get(status, (f"({_('status_unknown')})", "gray"))
        if self.app.root.winfo_exists() and self.winfo_exists():
            self.app.root.after(0, lambda: (
                self.servico_label_var.set(f"{base_text} {display_text}"),
                self.servico_label_widget.config(foreground=color)
            ))

    def _get_and_display_service_status_linux_thread_worker(self, service_name, base_text):
        status = self._verificar_status_servico_linux(service_name)
        _ = self.app.translator.get
        status_map = {
            "RUNNING": (f"({_('status_active_linux')})", "green"),
            "STOPPED": (f"({_('status_inactive_linux')})", "red"),
            "FAILED": (f"({_('status_failed_linux')})", "red"),
            "START_PENDING": (f"({_('status_activating_linux')})", "blue"),
            "STOP_PENDING": (f"({_('status_deactivating_linux')})", "blue"),
            "NOT_FOUND": (_('status_not_found_long'), "orange"),
            "ERROR": (_('status_error'), "red"), "SYSTEMCTL_NOT_FOUND": (f"({_('na_systemctl')})", "gray"),
            "UNKNOWN": (f"({_('status_unknown')})", "gray")
        }
        display_text, color = status_map.get(status, (f"({_('status_unknown')})", "gray"))
        if self.app.root.winfo_exists() and self.winfo_exists():
            self.app.root.after(0, lambda: (
                self.servico_label_var.set(f"{base_text} {display_text}"),
                self.servico_label_widget.config(foreground=color)
            ))

    def _verificar_status_servico_win(self, nome_servico_local):
        if not PYWIN32_AVAILABLE: return "ERROR"
        if not nome_servico_local: return "NOT_FOUND"
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            encodings_to_try = ['latin-1', 'utf-8', 'cp850', 'cp1252']
            output_text = None
            for enc in encodings_to_try:
                try:
                    result = subprocess.run(['sc', 'query', nome_servico_local], capture_output=True, text=False,
                                            check=False, startupinfo=startupinfo)
                    output_text = result.stdout.decode(enc, errors='replace') + result.stderr.decode(enc,
                                                                                                     errors='replace')
                    break
                except UnicodeDecodeError:
                    continue
            if output_text is None: return "ERROR"
            output_lower = output_text.lower()
            if any(err in output_lower for err in
                   ["failed 1060", "falha 1060", "does not exist as an installed service"]): return "NOT_FOUND"
            if "state" not in output_lower and "estado" not in output_lower: return "ERROR"
            if "running" in output_lower or "em execução" in output_lower: return "RUNNING"
            if "stopped" in output_lower or "parado" in output_lower: return "STOPPED"
            if "start_pending" in output_lower: return "START_PENDING"
            if "stop_pending" in output_lower: return "STOP_PENDING"
            return "UNKNOWN"
        except Exception:
            return "ERROR"

    def _verificar_status_servico_linux(self, nome_servico_local):
        if not SYSTEMCTL_AVAILABLE: return "SYSTEMCTL_NOT_FOUND"
        if not nome_servico_local: return "NOT_FOUND"
        nome_tentativa = f"{nome_servico_local}.service" if not nome_servico_local.endswith(
            ".service") else nome_servico_local
        try:
            cmd = ['systemctl', 'is-active', nome_tentativa]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            status = result.stdout.strip()
            if result.returncode == 0:
                if status == "active": return "RUNNING"
                if status == "activating": return "START_PENDING"
                if status == "deactivating": return "STOP_PENDING"
                if status == "failed": return "FAILED"
            elif result.returncode == 3:
                return "STOPPED"
            elif result.returncode == 4:
                return "NOT_FOUND"
            return "UNKNOWN"
        except Exception:
            return "ERROR"

    def start_log_monitoring(self):
        """Inicia a thread única de monitoramento e processamento de logs."""
        if self.log_monitor_thread and self.log_monitor_thread.is_alive():
            return

        if not self.pasta_raiz.get() or not os.path.isdir(self.pasta_raiz.get()):
            self.append_text_to_log_area(
                self.app.translator.get("log_warn_invalid_folder", folder=self.pasta_raiz.get()) + "\n")
            return

        self._stop_event.clear()
        self.log_monitor_thread = threading.Thread(
            target=self._log_processing_worker,
            daemon=True,
            name=f"LogWorker-Restarter-{self.nome}"
        )
        self.log_monitor_thread.start()

    def stop_log_monitoring(self, from_tab_closure=False):
        """Para a thread de monitoramento de logs de forma segura."""
        self._stop_event.set()
        if self.log_monitor_thread and self.log_monitor_thread.is_alive():
            if self.log_monitor_thread != threading.current_thread():
                self.log_monitor_thread.join(timeout=1.5)
        self.log_monitor_thread = None

    def restart_log_monitoring(self):
        """Para e reinicia o monitor de logs. Usado pelo botão '↻ Mon.'."""
        self.logger.info(f"Restarter [{self.nome}]: Manual log monitor restart triggered.")
        self.stop_log_monitoring()
        self.app.root.after(100, self.start_log_monitoring)

    def _log_processing_worker(self):
        self.logger.info(f"Restarter [{self.nome}]: Log processing worker started.")
        caminho_log_atual = None
        file_handle = None

        while not self._stop_event.is_set():
            try:
                if self._paused:
                    if self._stop_event.wait(0.5): break
                    continue

                log_filename = self.log_filename_var.get()
                pasta_raiz = self.pasta_raiz.get()
                subpasta_recente = self._obter_subpasta_log_mais_recente(pasta_raiz) if pasta_raiz and os.path.isdir(
                    pasta_raiz) else None

                if subpasta_recente:
                    novo_arquivo_log = os.path.join(subpasta_recente, log_filename)
                    if os.path.exists(novo_arquivo_log) and novo_arquivo_log != caminho_log_atual:
                        self.logger.info(f"Restarter [{self.nome}]: New log file detected: {novo_arquivo_log}")
                        if file_handle: file_handle.close()

                        caminho_log_atual = novo_arquivo_log
                        self.append_text_to_log_area_threadsafe(
                            self.app.translator.get("log_monitoring_file", file=caminho_log_atual))
                        file_handle = open(caminho_log_atual, 'r', encoding='latin-1', errors='replace')
                        file_handle.seek(0, os.SEEK_END)

                if file_handle:
                    current_filter = self.filtro_var.get().lower()
                    linha = file_handle.readline()
                    if linha:
                        self._process_log_line(linha, current_filter)
                        continue
            except ValueError:
                self.logger.warning(
                    f"Restarter [{self.nome}]: ValueError on read, likely file was closed. Rescanning...")
                if file_handle: file_handle.close()
                file_handle = None
                caminho_log_atual = None
                continue
            except Exception as e:
                self.logger.error(f"Restarter [{self.nome}]: Unhandled error in log worker loop: {e}", exc_info=True)
                if file_handle: file_handle.close()
                file_handle = None
                caminho_log_atual = None

            if self._stop_event.wait(1.0):
                break

        if file_handle:
            file_handle.close()
        self.logger.info(f"Restarter [{self.nome}]: Log processing worker stopped.")

    def _process_log_line(self, linha, current_filter):
        self.app.process_player_info_line(linha)
        if not current_filter or current_filter in linha.lower():
            self.append_text_to_log_area(linha)

        trigger_message_to_find = self.trigger_log_message_var.get()
        if trigger_message_to_find and trigger_message_to_find in linha.strip():
            self.logger.info(f"Restarter [{self.nome}]: Trigger detected. Line: '{linha.strip()}'.")
            if self.auto_restart_on_trigger_var.get():
                threading.Thread(target=self._delayed_restart_worker, daemon=True).start()

    def _obter_subpasta_log_mais_recente(self, pasta_raiz_logs):
        if not pasta_raiz_logs or not os.path.isdir(pasta_raiz_logs): return None
        try:
            log_folder_pattern = re.compile(r"^logs_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")
            subpastas_log_validas = [os.path.join(pasta_raiz_logs, nome) for nome in os.listdir(pasta_raiz_logs) if
                                     os.path.isdir(os.path.join(pasta_raiz_logs, nome)) and log_folder_pattern.match(
                                         nome)]
            return max(subpastas_log_validas, key=os.path.getmtime) if subpastas_log_validas else None
        except Exception:
            return None

    def _delayed_restart_worker(self):
        delay_s = self.restart_delay_after_trigger_var.get()
        self.append_text_to_log_area_threadsafe(self.app.translator.get("log_trigger_detected", delay=delay_s) + "\n")
        time.sleep(delay_s)
        self._executar_logica_reinicio_servico_efetivamente(is_scheduled_restart=False)

    def _executar_logica_reinicio_servico_efetivamente(self, is_scheduled_restart=False):
        _ = self.app.translator.get
        tipo_reinicio_msg_key = "restart_type_scheduled" if is_scheduled_restart else "restart_type_trigger"
        tipo_reinicio_msg = _(tipo_reinicio_msg_key)
        nome_servico = self.nome_servico.get()
        if not nome_servico:
            msg = _("log_error_no_service_for_restart", type=tipo_reinicio_msg) + "\n"
            self.append_text_to_log_area_threadsafe(msg)
            self.logger.error(f"Tab '{self.nome}': {msg.strip()}")
            return
        self.append_text_to_log_area_threadsafe(
            _("log_restart_process_started", type=tipo_reinicio_msg.upper(), service=nome_servico) + "\n")
        success = self._operar_servico_com_delays(nome_servico)
        if self.app.root.winfo_exists():
            if success:
                self.app.show_messagebox_from_thread("success", _("dialog_server_restarted_title", server=self.nome),
                                                     _("dialog_server_restarted_msg", service=nome_servico))
            else:
                self.app.show_messagebox_from_thread("error", _("dialog_restart_failed_title", server=self.nome),
                                                     _("dialog_restart_failed_msg", service=nome_servico))
            if self.winfo_exists(): self.update_service_status_display()

    def parar_servico_manual(self):
        _ = self.app.translator.get
        service_name = self.nome_servico.get()
        if not service_name:
            self.app.show_messagebox_from_thread("warning", _("warn_no_service_selected_title"),
                                                 _("warn_no_service_to_stop"))
            return
        threading.Thread(target=self._parar_servico_worker, args=(service_name,), daemon=True).start()

    def iniciar_servico_manual(self):
        _ = self.app.translator.get
        service_name = self.nome_servico.get()
        if not service_name:
            self.app.show_messagebox_from_thread("warning", _("warn_no_service_selected_title"),
                                                 _("warn_no_service_to_start"))
            return
        threading.Thread(target=self._iniciar_servico_worker, args=(service_name,), daemon=True).start()

    def _parar_servico_worker(self, service_name):
        _ = self.app.translator.get
        self.append_text_to_log_area_threadsafe(_("log_manual_stop", service=service_name) + "\n")
        success = self._stop_service(service_name)
        if success:
            self.app.show_messagebox_from_thread("success", _("info_service_stopped_title"),
                                                 _("info_service_stopped_msg", service=service_name))
        else:
            self.app.show_messagebox_from_thread("error", _("error_service_stop_failed_title"),
                                                 _("error_service_stop_failed_msg", service=service_name))
        self.update_service_status_display()

    def _iniciar_servico_worker(self, service_name):
        _ = self.app.translator.get
        self.append_text_to_log_area_threadsafe(_("log_manual_start", service=service_name) + "\n")
        success = self._start_service(service_name)
        if success:
            self.app.show_messagebox_from_thread("success", _("info_service_started_title"),
                                                 _("info_service_started_msg", service=service_name))
        else:
            self.app.show_messagebox_from_thread("error", _("error_service_start_failed_title"),
                                                 _("error_service_start_failed_msg", service=service_name))
        self.update_service_status_display()

    def _stop_service(self, service_name):
        _ = self.app.translator.get
        os_system = platform.system()
        try:
            if os_system == "Windows":
                self.append_text_to_log_area_threadsafe(_("log_executing_sc_stop", service=service_name) + "\n")
                startupinfo = subprocess.STARTUPINFO();
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(["sc", "stop", service_name], check=True, startupinfo=startupinfo, timeout=30)
            elif os_system == "Linux":
                nome_servico_systemd = f"{service_name}.service" if not service_name.endswith(
                    ".service") else service_name
                cmd_prefix = ['sudo'] if os.geteuid() != 0 else []
                self.append_text_to_log_area_threadsafe(
                    _("log_executing_sysd_stop", service=nome_servico_systemd) + "\n")
                subprocess.run(cmd_prefix + ['systemctl', 'stop', nome_servico_systemd], check=True,
                               capture_output=True, timeout=30)
            else:
                self.append_text_to_log_area_threadsafe(_("log_unsupported_os_control", os=os_system) + "\n")
                return False
            self.append_text_to_log_area_threadsafe(_("log_stop_cmd_sent", service=service_name) + "\n")
            return True
        except Exception as e:
            self.append_text_to_log_area_threadsafe(_("log_stop_error", service=service_name, error=e) + "\n")
            self.logger.error(f"Erro ao parar serviço '{service_name}': {e}", exc_info=True)
            return False

    def _start_service(self, service_name):
        _ = self.app.translator.get
        os_system = platform.system()
        try:
            if os_system == "Windows":
                self.append_text_to_log_area_threadsafe(_("log_executing_sc_start", service=service_name) + "\n")
                startupinfo = subprocess.STARTUPINFO();
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(["sc", "start", service_name], check=True, startupinfo=startupinfo, timeout=30)
            elif os_system == "Linux":
                nome_servico_systemd = f"{service_name}.service" if not service_name.endswith(
                    ".service") else service_name
                cmd_prefix = ['sudo'] if os.geteuid() != 0 else []
                self.append_text_to_log_area_threadsafe(
                    _("log_executing_sysd_start", service=nome_servico_systemd) + "\n")
                subprocess.run(cmd_prefix + ['systemctl', 'start', nome_servico_systemd], check=True,
                               capture_output=True, timeout=30)
            else:
                self.append_text_to_log_area_threadsafe(_("log_unsupported_os_control", os=os_system) + "\n")
                return False
            self.append_text_to_log_area_threadsafe(_("log_start_cmd_sent", service=service_name) + "\n")
            return True
        except Exception as e:
            self.append_text_to_log_area_threadsafe(_("log_start_error", service=service_name, error=e) + "\n")
            self.logger.error(f"Erro ao iniciar serviço '{service_name}': {e}", exc_info=True)
            return False

    def _operar_servico_com_delays(self, nome_servico):
        _ = self.app.translator.get
        stop_delay, start_delay = self.stop_delay_var.get(), self.start_delay_var.get()
        status_win = self._verificar_status_servico_win(nome_servico)
        status_linux = self._verificar_status_servico_linux(nome_servico)
        if status_win == "RUNNING" or status_linux == "RUNNING":
            if not self._stop_service(nome_servico):
                self.append_text_to_log_area_threadsafe(_("log_restart_abort", service=nome_servico) + "\n")
                return False
            self.append_text_to_log_area_threadsafe(_("log_wait_after_stop", delay=stop_delay) + "\n")
            time.sleep(stop_delay)
        if not self._start_service(nome_servico):
            self.append_text_to_log_area_threadsafe(
                _("log_start_error", service=nome_servico, error="").strip() + ".\n")
            return False
        self.append_text_to_log_area_threadsafe(_("log_wait_after_start", delay=start_delay) + "\n")
        time.sleep(start_delay)
        final_status_win = self._verificar_status_servico_win(nome_servico)
        final_status_linux = self._verificar_status_servico_linux(nome_servico)
        return final_status_win == "RUNNING" or final_status_linux == "RUNNING"

    def append_text_to_log_area(self, texto):
        if self.winfo_exists():
            try:
                self.app.root.after(0, self._append_text_to_log_area_gui_thread, texto)
            except:
                pass

    def _append_text_to_log_area_gui_thread(self, texto):
        if not self.text_area_log.winfo_exists(): return
        try:
            self.text_area_log.config(state='normal')
            self.text_area_log.insert('end', texto)
            if self.auto_scroll_log_var.get(): self.text_area_log.yview_moveto(1.0)
            self.text_area_log.config(state='disabled')
        except tk.TclError:
            pass

    def append_text_to_log_area_threadsafe(self, texto):
        self.append_text_to_log_area(texto)

    def limpar_tela_log(self):
        if self.text_area_log.winfo_exists():
            self.text_area_log.config(state='normal')
            self.text_area_log.delete('1.0', 'end')
            self.text_area_log.config(state='disabled')

    def toggle_pausa(self):
        self._paused = not self._paused
        _ = self.app.translator.get
        btn_text, btn_style = (_('btn_resume'), SUCCESS) if self._paused else (_('btn_pause'), WARNING)
        self.pausar_btn.config(text=btn_text, bootstyle=btn_style)

    def _toggle_log_search_bar(self, event=None, force_show=False, force_hide=False):
        if not hasattr(self, 'search_log_frame') or not self.search_log_frame.winfo_exists(): return
        if force_hide or (self.search_log_frame.winfo_ismapped() and not force_show):
            self.search_log_frame.pack_forget()
            if self.text_area_log.winfo_exists(): self.text_area_log.tag_remove("search_match", "1.0", "end")
        elif self.text_area_log.winfo_exists():
            self.search_log_frame.pack(fill='x', before=self.text_area_log, pady=(0, 2), padx=5)
            if self.log_search_entry.winfo_exists(): self.log_search_entry.focus_set()

    def _perform_log_search_internal(self, term, start_pos, direction_forward=True, wrap=True):
        if not term or not self.text_area_log.winfo_exists(): return None
        self.text_area_log.config(state="normal")
        self.text_area_log.tag_remove("search_match", "1.0", "end")
        count_var = tk.IntVar()
        pos = self.text_area_log.search(term, start_pos, backwards=(not direction_forward), count=count_var,
                                        nocase=True, stopindex="1.0" if not direction_forward else "end")
        if pos:
            end_pos = f"{pos}+{count_var.get()}c"
            self.text_area_log.tag_add("search_match", pos, end_pos)
            self.text_area_log.tag_config("search_match", background="yellow", foreground="black")
            self.text_area_log.see(pos)
            self.text_area_log.config(state='disabled')
            return end_pos if direction_forward else pos
        elif wrap:
            wrap_start = "1.0" if direction_forward else "end"
            return self._perform_log_search_internal(term, wrap_start, direction_forward, wrap=False)
        self.text_area_log.config(state='disabled')
        return None

    def _search_log_next(self, event=None):
        term = self.log_search_var.get()
        if not term: return
        start_from = self.last_search_pos
        current_match = self.text_area_log.tag_ranges("search_match")
        if current_match: start_from = current_match[1]
        next_pos = self._perform_log_search_internal(term, start_from, True, True)
        if next_pos: self.last_search_pos = next_pos

    def _search_log_prev(self, event=None):
        term = self.log_search_var.get()
        if not term: return
        start_from = self.last_search_pos
        current_match = self.text_area_log.tag_ranges("search_match")
        if current_match: start_from = current_match[0]
        prev_pos = self._perform_log_search_internal(term, start_from, False, True)
        if prev_pos: self.last_search_pos = prev_pos


# ==============================================================================
# CLASSE VotemapTab (Originalmente ServidorTab de PQDT_Raphael_Votemappatch.py)
# ==============================================================================
class VotemapTab(ttk.Frame):
    def __init__(self, master_notebook, app_instance, nome_servidor, config_dict=None):
        super().__init__(master_notebook)
        self.app = app_instance
        self.nome = nome_servidor
        self.config_inicial = config_dict if config_dict else {}
        self.logger = votemap_logger

        # --- Variáveis de Estado (tk.Variables) ---
        self.pasta_raiz = tk.StringVar(value=self.config_inicial.get("log_folder", ""))
        self.arquivo_json = tk.StringVar(value=self.config_inicial.get("server_json", ""))
        self.arquivo_json_votemap = tk.StringVar(value=self.config_inicial.get("votemap_json", ""))
        self.nome_servico = tk.StringVar(value=self.config_inicial.get("service_name", ""))
        self.log_filename_var = tk.StringVar(value=self.config_inicial.get("log_filename", "console.log"))
        self.log_folder_path_label_var = tk.StringVar()
        self.server_json_path_label_var = tk.StringVar()
        self.votemap_json_path_label_var = tk.StringVar()
        self.servico_label_var = tk.StringVar()
        self.filtro_var = tk.StringVar(value=self.config_inicial.get("filter", ""))
        self.auto_restart_var = tk.BooleanVar(value=self.config_inicial.get("auto_restart", True))
        self.vote_pattern_var = tk.StringVar(value=self.config_inicial.get("vote_pattern", r"\.EndVote\(\)"))
        self.winner_pattern_var = tk.StringVar(value=self.config_inicial.get("winner_pattern", r"Winner: \[(\d+)\]"))
        self.default_mission_var = tk.StringVar(
            value=self.config_inicial.get("default_mission", "{B88CC33A14B71FDC}Missions/V30_MapVoting_Mission.conf"))
        self.stop_delay_var = tk.IntVar(value=self.config_inicial.get("stop_delay", 10))
        self.start_delay_var = tk.IntVar(value=self.config_inicial.get("start_delay", 30))
        self.auto_scroll_log_var = tk.BooleanVar(value=self.config_inicial.get("auto_scroll_log", True))
        self.log_search_var = tk.StringVar()
        self.last_search_pos = "1.0"
        self.aguardando_winner = False

        # --- Threads e Eventos ---
        self._stop_event = threading.Event()
        self._paused = False
        self.log_monitor_thread = None

        self._create_ui_for_tab()
        self.update_ui_text()
        self.initialize_from_config_vars()

        vars_to_trace = [
            self.pasta_raiz, self.arquivo_json, self.arquivo_json_votemap, self.nome_servico,
            self.filtro_var, self.log_filename_var, self.vote_pattern_var, self.winner_pattern_var,
            self.default_mission_var, self.auto_restart_var, self.auto_scroll_log_var,
            self.stop_delay_var, self.start_delay_var
        ]
        for var in vars_to_trace:
            var.trace_add("write", lambda *args: self._value_changed())

    def _value_changed(self):
        self.app.mark_config_changed()

    def get_current_config(self):
        return {
            "nome": self.nome,
            "log_folder": self.pasta_raiz.get(),
            "server_json": self.arquivo_json.get(),
            "votemap_json": self.arquivo_json_votemap.get(),
            "service_name": self.nome_servico.get(),
            "log_filename": self.log_filename_var.get(),
            "filter": self.filtro_var.get(),
            "auto_restart": self.auto_restart_var.get(),
            "vote_pattern": self.vote_pattern_var.get(),
            "winner_pattern": self.winner_pattern_var.get(),
            "default_mission": self.default_mission_var.get(),
            "stop_delay": self.stop_delay_var.get(),
            "start_delay": self.start_delay_var.get(),
            "auto_scroll_log": self.auto_scroll_log_var.get(),
        }

    def _create_ui_for_tab(self):
        outer_top_frame = ttk.Frame(self)
        outer_top_frame.pack(pady=5, padx=5, fill='x')

        self.selection_labelframe = ttk.Labelframe(outer_top_frame, padding=(10, 5))
        self.selection_labelframe.pack(side='top', fill='x', pady=(0, 5))

        path_buttons_frame = ttk.Frame(self.selection_labelframe)
        path_buttons_frame.pack(fill='x')

        self.selecionar_btn = ttk.Button(path_buttons_frame, command=self.selecionar_pasta, bootstyle=PRIMARY)
        self.selecionar_btn.pack(side='left', pady=2, padx=(0, 2))
        self.selecionar_btn_tooltip = ToolTip(self.selecionar_btn)
        self.json_btn = ttk.Button(path_buttons_frame, command=self.selecionar_arquivo_json_servidor, bootstyle=INFO)
        self.json_btn.pack(side='left', padx=2, pady=2)
        self.json_btn_tooltip = ToolTip(self.json_btn)
        self.json_vm_btn = ttk.Button(path_buttons_frame, command=self.selecionar_arquivo_json_votemap, bootstyle=INFO)
        self.json_vm_btn.pack(side='left', padx=2, pady=2)
        self.json_vm_btn_tooltip = ToolTip(self.json_vm_btn)
        self.servico_btn = ttk.Button(path_buttons_frame, command=self.selecionar_servico, bootstyle=SECONDARY)
        self.servico_btn.pack(side='left', padx=2, pady=2)
        self.servico_btn_tooltip = ToolTip(self.servico_btn)
        self.iniciar_servico_btn = ttk.Button(path_buttons_frame, command=self.iniciar_servico_manual,
                                              bootstyle=SUCCESS)
        self.iniciar_servico_btn.pack(side='left', padx=(5, 2), pady=2)
        self.iniciar_servico_btn_tooltip = ToolTip(self.iniciar_servico_btn)
        self.parar_servico_btn = ttk.Button(path_buttons_frame, command=self.parar_servico_manual, bootstyle=DANGER)
        self.parar_servico_btn.pack(side='left', padx=2, pady=2)
        self.parar_servico_btn_tooltip = ToolTip(self.parar_servico_btn)
        self.refresh_servico_status_btn = ttk.Button(path_buttons_frame, command=self.update_service_status_display,
                                                     bootstyle=(TOOLBUTTON, LIGHT), width=2)
        self.refresh_servico_status_btn.pack(side='left', padx=(5, 2), pady=2)
        self.refresh_servico_status_btn_tooltip = ToolTip(self.refresh_servico_status_btn)

        path_labels_frame_line1 = ttk.Frame(self.selection_labelframe)
        path_labels_frame_line1.pack(fill='x', pady=(5, 2))
        self.log_folder_path_label = ttk.Label(path_labels_frame_line1, textvariable=self.log_folder_path_label_var,
                                               wraplength=450, anchor='w')
        self.log_folder_path_label.pack(side='left', padx=5, fill='x', expand=True)
        self.servico_label_widget = ttk.Label(path_labels_frame_line1, textvariable=self.servico_label_var, anchor='w',
                                              width=30)
        self.servico_label_widget.pack(side='left', padx=(5, 0))

        path_labels_frame_line2 = ttk.Frame(self.selection_labelframe)
        path_labels_frame_line2.pack(fill='x', pady=(0, 0))
        self.json_server_path_label = ttk.Label(path_labels_frame_line2, textvariable=self.server_json_path_label_var,
                                                wraplength=220, anchor='w')
        self.json_server_path_label.pack(side='left', padx=5, fill='x', expand=True)
        self.json_votemap_path_label = ttk.Label(path_labels_frame_line2,
                                                 textvariable=self.votemap_json_path_label_var,
                                                 wraplength=220, anchor='w')
        self.json_votemap_path_label.pack(side='left', padx=5, fill='x', expand=True)

        self.controls_labelframe = ttk.Labelframe(outer_top_frame, padding=(10, 5))
        self.controls_labelframe.pack(side='top', fill='x', pady=(5, 0))
        log_controls_subframe = ttk.Frame(self.controls_labelframe)
        log_controls_subframe.pack(fill='x', expand=True)
        self.filtro_lbl = ttk.Label(log_controls_subframe)
        self.filtro_lbl.pack(side='left', padx=(0, 5))
        self.filtro_entry = ttk.Entry(log_controls_subframe, textvariable=self.filtro_var, width=20)
        self.filtro_entry.pack(side='left', padx=(0, 5))
        self.filtro_entry_tooltip = ToolTip(self.filtro_entry)
        self.refresh_json_btn = ttk.Button(log_controls_subframe, command=self.forcar_refresh_json_display,
                                           bootstyle=SUCCESS)
        self.refresh_json_btn.pack(side='left', padx=5)
        self.refresh_json_btn_tooltip = ToolTip(self.refresh_json_btn)
        self.pausar_btn = ttk.Button(log_controls_subframe, command=self.toggle_pausa, bootstyle=WARNING)
        self.pausar_btn.pack(side='left', padx=5)
        self.pausar_btn_tooltip = ToolTip(self.pausar_btn)
        self.limpar_btn = ttk.Button(log_controls_subframe, command=self.limpar_tela_log, bootstyle=SECONDARY)
        self.limpar_btn.pack(side='left', padx=5)
        self.limpar_btn_tooltip = ToolTip(self.limpar_btn)
        self.restart_monitor_btn = ttk.Button(log_controls_subframe, command=self.restart_log_monitoring,
                                              bootstyle=(TOOLBUTTON, INFO))
        self.restart_monitor_btn.pack(side='left', padx=5)
        self.restart_monitor_btn_tooltip = ToolTip(self.restart_monitor_btn)

        self.tab_notebook = ttk.Notebook(self)
        self.tab_notebook.pack(fill='both', expand=True, padx=5, pady=(5, 5))

        self.log_frame = ttk.Frame(self.tab_notebook)
        self.tab_notebook.add(self.log_frame)
        self.log_label_display = ttk.Label(self.log_frame, foreground="red")
        self.log_label_display.pack(pady=(5, 0))
        self.search_log_frame = ttk.Frame(self.log_frame)
        self.search_lbl = ttk.Label(self.search_log_frame)
        self.search_lbl.pack(side='left', padx=(5, 2))
        self.log_search_entry = ttk.Entry(self.search_log_frame, textvariable=self.log_search_var)
        self.log_search_entry.pack(side='left', fill='x', expand=True, padx=2)
        self.log_search_entry.bind("<Return>", self._search_log_next)
        self.search_next_btn = ttk.Button(self.search_log_frame, command=self._search_log_next, bootstyle=SECONDARY)
        self.search_next_btn.pack(side='left', padx=2)
        self.search_prev_btn = ttk.Button(self.search_log_frame, command=self._search_log_prev, bootstyle=SECONDARY)
        self.search_prev_btn.pack(side='left', padx=2)
        self.close_search_btn = ttk.Button(self.search_log_frame, command=self._toggle_log_search_bar,
                                           bootstyle=(SECONDARY, DANGER), width=2)
        self.close_search_btn.pack(side='left', padx=(2, 5))

        self.text_area_log = ScrolledText(self.log_frame, wrap='word', height=10, state='disabled')
        self.text_area_log.pack(fill='both', expand=True, pady=(0, 5))
        self.text_area_log.bind("<Control-f>", lambda e: self._toggle_log_search_bar(force_show=True))
        self.auto_scroll_check = ttk.Checkbutton(self.log_frame, variable=self.auto_scroll_log_var)
        self.auto_scroll_check.pack(side='left', anchor='sw', pady=2, padx=5)

        self.json_server_frame = ttk.Frame(self.tab_notebook)
        self.tab_notebook.add(self.json_server_frame)
        self.json_server_lbl = ttk.Label(self.json_server_frame, foreground="blue")
        self.json_server_lbl.pack(pady=(5, 0))
        self.json_text_area_server = ScrolledText(self.json_server_frame, wrap='word', height=10, state='disabled')
        self.json_text_area_server.pack(fill='both', expand=True, padx=5, pady=5)

        self.json_votemap_frame = ttk.Frame(self.tab_notebook)
        self.tab_notebook.add(self.json_votemap_frame)
        self.json_votemap_lbl = ttk.Label(self.json_votemap_frame, foreground="blue")
        self.json_votemap_lbl.pack(pady=(5, 0))
        self.json_text_area_votemap = ScrolledText(self.json_votemap_frame, wrap='word', height=10, state='disabled')
        self.json_text_area_votemap.pack(fill='both', expand=True, padx=5, pady=5)

        self.options_votemap_frame = ttk.Frame(self.tab_notebook)
        self.tab_notebook.add(self.options_votemap_frame)
        options_inner_frame = ttk.Frame(self.options_votemap_frame, padding=15)
        options_inner_frame.pack(fill='both', expand=True)
        self.auto_restart_check = ttk.Checkbutton(options_inner_frame, variable=self.auto_restart_var)
        self.auto_restart_check.grid(row=0, column=0, sticky='w', padx=5, pady=5, columnspan=2)
        self.auto_restart_check_tooltip = ToolTip(self.auto_restart_check)
        self.vote_pattern_lbl = ttk.Label(options_inner_frame)
        self.vote_pattern_lbl.grid(row=1, column=0, sticky='w', padx=5, pady=(10, 0))
        self.vote_pattern_entry = ttk.Entry(options_inner_frame, textvariable=self.vote_pattern_var, width=60)
        self.vote_pattern_entry.grid(row=2, column=0, sticky='ew', padx=5, pady=2, columnspan=2)
        self.vote_pattern_entry_tooltip = ToolTip(self.vote_pattern_entry)
        self.winner_pattern_lbl = ttk.Label(options_inner_frame)
        self.winner_pattern_lbl.grid(row=3, column=0, sticky='w', padx=5, pady=(10, 0))
        self.winner_pattern_entry = ttk.Entry(options_inner_frame, textvariable=self.winner_pattern_var, width=60)
        self.winner_pattern_entry.grid(row=4, column=0, sticky='ew', padx=5, pady=2, columnspan=2)
        self.winner_pattern_entry_tooltip = ToolTip(self.winner_pattern_entry)
        self.default_mission_lbl = ttk.Label(options_inner_frame)
        self.default_mission_lbl.grid(row=5, column=0, sticky='w', padx=5, pady=(10, 0))
        self.default_mission_entry = ttk.Entry(options_inner_frame, textvariable=self.default_mission_var, width=60)
        self.default_mission_entry.grid(row=6, column=0, sticky='ew', padx=5, pady=2, columnspan=2)
        self.default_mission_entry_tooltip = ToolTip(self.default_mission_entry)

        self.log_filename_lbl = ttk.Label(options_inner_frame)
        self.log_filename_lbl.grid(row=7, column=0, sticky='w', padx=5, pady=(10, 0))
        self.log_filename_entry = ttk.Entry(options_inner_frame, textvariable=self.log_filename_var, width=60)
        self.log_filename_entry.grid(row=8, column=0, sticky='ew', padx=5, pady=2, columnspan=2)
        self.log_filename_entry_tooltip = ToolTip(self.log_filename_entry)

        delay_frame = ttk.Frame(options_inner_frame)
        delay_frame.grid(row=9, column=0, columnspan=2, sticky='ew', pady=(10, 0))
        self.stop_delay_lbl = ttk.Label(delay_frame)
        self.stop_delay_lbl.pack(side='left', padx=5)
        self.stop_delay_spinbox = ttk.Spinbox(delay_frame, from_=1, to=60, textvariable=self.stop_delay_var, width=5)
        self.stop_delay_spinbox.pack(side='left', padx=5)
        self.start_delay_lbl = ttk.Label(delay_frame)
        self.start_delay_lbl.pack(side='left', padx=15)
        self.start_delay_spinbox = ttk.Spinbox(delay_frame, from_=5, to=180, textvariable=self.start_delay_var, width=5)
        self.start_delay_spinbox.pack(side='left', padx=5)
        options_inner_frame.columnconfigure(0, weight=1)

    def update_ui_text(self):
        _ = self.app.translator.get

        self.selection_labelframe.config(text=_('votemap_tab_paths_and_service'))
        self.selecionar_btn.config(text=_('btn_select_log_folder'))
        self.selecionar_btn_tooltip.text = _('tooltip_select_log_folder')
        self.json_btn.config(text=_('btn_select_server_json'))
        self.json_btn_tooltip.text = _('tooltip_select_server_json')
        self.json_vm_btn.config(text=_('btn_select_votemap_json'))
        self.json_vm_btn_tooltip.text = _('tooltip_select_votemap_json')
        self.servico_btn.config(text=_('btn_select_service'))
        self.servico_btn_tooltip.text = _('tooltip_select_service')
        self.iniciar_servico_btn.config(text=_('btn_start_service'))
        self.iniciar_servico_btn_tooltip.text = _('tooltip_start_service')
        self.parar_servico_btn.config(text=_('btn_stop_service'))
        self.parar_servico_btn_tooltip.text = _('tooltip_stop_service')
        self.refresh_servico_status_btn.config(text=_('btn_refresh_status'))
        self.refresh_servico_status_btn_tooltip.text = _('tooltip_refresh_status')

        self.controls_labelframe.config(text=_('lbl_log_controls'))
        self.filtro_lbl.config(text=_('lbl_filter'))
        self.filtro_entry_tooltip.text = _('tooltip_filter')
        self.refresh_json_btn.config(text=_('btn_refresh_jsons'))
        self.refresh_json_btn_tooltip.text = _('tooltip_btn_refresh_jsons')
        self.pausar_btn.config(text=_('btn_resume') if self._paused else _('btn_pause'))
        self.pausar_btn_tooltip.text = _('tooltip_pause_resume')
        self.limpar_btn.config(text=_('btn_clear_log'))
        self.limpar_btn_tooltip.text = _('tooltip_clear_log')
        self.restart_monitor_btn.config(text=_('btn_restart_monitor'))
        self.restart_monitor_btn_tooltip.text = _('tooltip_restart_monitor')

        self.tab_notebook.tab(self.log_frame, text=_('lbl_server_logs'))
        self.log_label_display.config(text=_('lbl_live_log'))
        self.search_lbl.config(text=_('lbl_search'))
        self.search_next_btn.config(text=_('btn_next'))
        self.search_prev_btn.config(text=_('btn_previous'))
        self.close_search_btn.config(text=_('btn_close_search'))
        self.auto_scroll_check.config(text=_('chk_auto_scroll'))

        self.tab_notebook.tab(self.json_server_frame, text=_('tab_json_server'))
        self.json_server_lbl.config(text=_('lbl_content_json_server'))
        self.tab_notebook.tab(self.json_votemap_frame, text=_('tab_json_votemap'))
        self.json_votemap_lbl.config(text=_('lbl_content_json_votemap'))

        self.tab_notebook.tab(self.options_votemap_frame, text=_('tab_votemap_options'))
        self.auto_restart_check.config(text=_('votemap_chk_auto_restart'))
        self.auto_restart_check_tooltip.text = _('tooltip_votemap_chk_auto_restart')
        self.vote_pattern_lbl.config(text=_('votemap_lbl_vote_pattern'))
        self.vote_pattern_entry_tooltip.text = _('tooltip_votemap_vote_pattern')
        self.winner_pattern_lbl.config(text=_('votemap_lbl_winner_pattern'))
        self.winner_pattern_entry_tooltip.text = _('tooltip_votemap_winner_pattern')
        self.default_mission_lbl.config(text=_('votemap_lbl_default_mission'))
        self.default_mission_entry_tooltip.text = _('tooltip_votemap_default_mission')
        self.log_filename_lbl.config(text=_('lbl_log_filename'))
        self.log_filename_entry_tooltip.text = _('tooltip_log_filename')
        self.stop_delay_lbl.config(text=_('lbl_stop_delay_short'))
        self.start_delay_lbl.config(text=_('lbl_start_delay_short'))

        self.initialize_from_config_vars()

    def _update_manual_control_button_states(self):
        has_service = bool(self.nome_servico.get())
        os_system = platform.system()
        can_manage = (os_system == "Windows" and PYWIN32_AVAILABLE) or (os_system == "Linux" and SYSTEMCTL_AVAILABLE)
        new_state = NORMAL if has_service and can_manage else DISABLED
        if hasattr(self,
                   'iniciar_servico_btn') and self.iniciar_servico_btn.winfo_exists(): self.iniciar_servico_btn.config(
            state=new_state)
        if hasattr(self, 'parar_servico_btn') and self.parar_servico_btn.winfo_exists(): self.parar_servico_btn.config(
            state=new_state)

    def initialize_from_config_vars(self):
        _ = self.app.translator.get
        default_fg = self.app.style.colors.fg if hasattr(self.app.style, 'colors') else "black"

        log_folder_prefix = _('lbl_log_folder_prefix')
        pasta_raiz_val = self.pasta_raiz.get()
        if pasta_raiz_val and os.path.isdir(pasta_raiz_val):
            self.log_folder_path_label_var.set(f"{log_folder_prefix}: {os.path.basename(pasta_raiz_val)}")
            self.log_folder_path_label.config(foreground="green")
            self.start_log_monitoring()
        elif pasta_raiz_val:
            self.log_folder_path_label_var.set(
                f"{log_folder_prefix} ({_('status_invalid')}): {os.path.basename(pasta_raiz_val)}")
            self.log_folder_path_label.config(foreground="red")
        else:
            self.log_folder_path_label_var.set(f"{log_folder_prefix}: {_('status_none')}")
            self.log_folder_path_label.config(foreground=default_fg)

        self.forcar_refresh_json_display()
        os_system = platform.system()
        can_manage_services = (os_system == "Windows" and PYWIN32_AVAILABLE) or (
                os_system == "Linux" and SYSTEMCTL_AVAILABLE)
        self.servico_btn.config(state=NORMAL if can_manage_services else DISABLED)
        self.refresh_servico_status_btn.config(
            state=NORMAL if can_manage_services and self.nome_servico.get() else DISABLED)

        service_prefix = _('lbl_service_prefix')
        if self.nome_servico.get():
            self.update_service_status_display()
        elif not can_manage_services:
            reason = _('na_pywin32') if os_system == "Windows" else _('na_systemctl') if os_system == "Linux" else _(
                'na_os', os=os_system)
            self.servico_label_var.set(f"{service_prefix}: {reason}")
            self.servico_label_widget.config(foreground="gray")
        else:
            self.servico_label_var.set(f"{service_prefix}: {_('status_none')}")
            self.servico_label_widget.config(foreground="orange")
        self._update_manual_control_button_states()

    def forcar_refresh_json_display(self):
        self._refresh_single_json_display(self.arquivo_json.get(), self.json_text_area_server,
                                          self.server_json_path_label_var, self.json_server_path_label, "server")
        self._refresh_single_json_display(self.arquivo_json_votemap.get(), self.json_text_area_votemap,
                                          self.votemap_json_path_label_var, self.json_votemap_path_label, "votemap")

    def _refresh_single_json_display(self, file_path, text_widget, label_var, label_widget, json_type):
        _ = self.app.translator.get
        prefix = _(f'lbl_{json_type}_json_prefix')
        default_fg = self.app.style.colors.fg if hasattr(self.app.style, 'colors') else "black"
        if file_path:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    json_data = json.loads(content)
                    self._display_json_in_widget(text_widget, json_data)
                    label_var.set(f"{prefix}: {os.path.basename(file_path)}")
                    label_widget.config(foreground="green")
                except json.JSONDecodeError as e:
                    error_msg = _('json_decode_error', error=e)
                    self.logger.error(f"Failed to decode {json_type} JSON {file_path}: {e}")
                    self._display_json_in_widget(text_widget, error_msg)
                    label_var.set(f"{prefix} ({_('status_invalid')}): {os.path.basename(file_path)}")
                    label_widget.config(foreground="red")
                except Exception as e:
                    error_msg = _('json_display_error', error=e)
                    self.logger.error(f"Failed to read {json_type} JSON {file_path}: {e}")
                    self._display_json_in_widget(text_widget, error_msg)
                    label_var.set(f"{prefix} ({_('status_invalid')}): {os.path.basename(file_path)}")
                    label_widget.config(foreground="red")
            else:
                self._display_json_in_widget(text_widget, _('json_display_not_found'))
                label_var.set(f"{prefix} ({_('status_not_found_short')}): {os.path.basename(file_path)}")
                label_widget.config(foreground="orange")
        else:
            self._display_json_in_widget(text_widget, _('json_display_not_configured'))
            label_var.set(f"{prefix}: {_('status_none')}")
            label_widget.config(foreground=default_fg)

    def _display_json_in_widget(self, text_widget, content):
        dados_formatados = json.dumps(content, indent=4, ensure_ascii=False) if isinstance(content,
                                                                                           (dict, list)) else str(
            content)
        if self.winfo_exists() and text_widget.winfo_exists():
            text_widget.configure(state='normal')
            text_widget.delete('1.0', 'end')
            text_widget.insert('end', dados_formatados)
            text_widget.configure(state='disabled')

    def selecionar_pasta(self):
        pasta_selecionada = filedialog.askdirectory(
            title=self.app.translator.get("dialog_select_folder_title", server=self.nome))
        if pasta_selecionada:
            self.stop_log_monitoring()
            self.pasta_raiz.set(pasta_selecionada)
            self.initialize_from_config_vars()

    def _selecionar_arquivo_json_generico(self, title_key, var_caminho):
        _ = self.app.translator.get
        caminho_selecionado = filedialog.askopenfilename(
            title=_(title_key, server=self.nome),
            filetypes=[(_('json_file_filter_name'), "*.json"), (_('all_files_filter_name'), "*.*")])
        if caminho_selecionado:
            var_caminho.set(caminho_selecionado)
            self.forcar_refresh_json_display()

    def selecionar_arquivo_json_servidor(self):
        self._selecionar_arquivo_json_generico("dialog_select_server_json_title", self.arquivo_json)

    def selecionar_arquivo_json_votemap(self):
        self._selecionar_arquivo_json_generico("dialog_select_votemap_json_title", self.arquivo_json_votemap)

    def selecionar_servico(self):
        os_system = platform.system()
        if os_system == "Windows":
            self.app.iniciar_selecao_servico_para_aba(self, "windows")
        elif os_system == "Linux":
            self.app.iniciar_selecao_servico_para_aba(self, "linux")
        else:
            self.app.show_messagebox_from_thread("warning", self.app.translator.get("dialog_unsupported_os_title"),
                                                 self.app.translator.get("dialog_unsupported_os_votemap", os=os_system))

    def set_selected_service(self, service_name):
        if self.nome_servico.get() != service_name:
            self.nome_servico.set(service_name)
            self.update_service_status_display()
            self.app.set_status_from_thread(
                self.app.translator.get("status_service_selected", service=service_name, server=self.nome))
            self.logger.info(f"Tab '{self.nome}': Serviço selecionado: {service_name}")
        self._update_manual_control_button_states()

    def update_service_status_display(self):
        service_name = self.nome_servico.get()
        if not service_name: self.initialize_from_config_vars(); return
        _ = self.app.translator.get
        base_text = f"{_('lbl_service_prefix')}: {service_name}"
        self.servico_label_var.set(f"{base_text} ({_('status_checking')})")
        self.servico_label_widget.config(foreground="blue")
        os_system = platform.system()
        worker_func = None
        if os_system == "Windows" and PYWIN32_AVAILABLE:
            worker_func = self._get_and_display_service_status_win_thread_worker
        elif os_system == "Linux" and SYSTEMCTL_AVAILABLE:
            worker_func = self._get_and_display_service_status_linux_thread_worker
        if worker_func:
            threading.Thread(target=worker_func, args=(service_name, base_text), daemon=True).start()
        else:
            self.initialize_from_config_vars()

    def _get_and_display_service_status_win_thread_worker(self, service_name, base_text):
        status = self._verificar_status_servico_win(service_name)
        _ = self.app.translator.get
        status_map = {
            "RUNNING": (_('status_running_win'), "green"), "STOPPED": (_('status_stopped_win'), "red"),
            "NOT_FOUND": (_('status_not_found_long'), "orange"), "ERROR": (_('status_error'), "red")
        }
        display_text, color = status_map.get(status, (_('status_unknown'), "gray"))
        if self.app.root.winfo_exists() and self.winfo_exists():
            self.app.root.after(0, lambda: (self.servico_label_var.set(f"{base_text} {display_text}"),
                                            self.servico_label_widget.config(foreground=color)))

    def _get_and_display_service_status_linux_thread_worker(self, service_name, base_text):
        status = self._verificar_status_servico_linux(service_name)
        _ = self.app.translator.get
        status_map = {
            "RUNNING": (f"({_('status_active_linux')})", "green"),
            "STOPPED": (f"({_('status_inactive_linux')})", "red"),
            "FAILED": (f"({_('status_failed_linux')})", "red"), "NOT_FOUND": (_('status_not_found_long'), "orange"),
            "ERROR": (_('status_error'), "red")
        }
        display_text, color = status_map.get(status, (f"({_('status_unknown')})", "gray"))
        if self.app.root.winfo_exists() and self.winfo_exists():
            self.app.root.after(0, lambda: (self.servico_label_var.set(f"{base_text} {display_text}"),
                                            self.servico_label_widget.config(foreground=color)))

    def _verificar_status_servico_win(self, nome_servico_local):
        if not PYWIN32_AVAILABLE: return "ERROR"
        if not nome_servico_local: return "NOT_FOUND"
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(['sc', 'query', nome_servico_local], capture_output=True, text=True,
                                    errors='ignore', startupinfo=startupinfo)
            if "failed 1060" in result.stdout.lower(): return "NOT_FOUND"
            if "RUNNING" in result.stdout: return "RUNNING"
            if "STOPPED" in result.stdout: return "STOPPED"
            return "UNKNOWN"
        except Exception:
            return "ERROR"

    def _verificar_status_servico_linux(self, nome_servico_local):
        if not SYSTEMCTL_AVAILABLE: return "ERROR"
        if not nome_servico_local: return "NOT_FOUND"
        nome_servico_systemd = f"{nome_servico_local}.service" if not nome_servico_local.endswith(
            ".service") else nome_servico_local
        try:
            result = subprocess.run(['systemctl', 'is-active', nome_servico_systemd], capture_output=True, text=True)
            status = result.stdout.strip()
            if status == "active": return "RUNNING"
            if status == "inactive": return "STOPPED"
            if status == "failed": return "FAILED"
            return "UNKNOWN"
        except Exception:
            return "ERROR"

    def start_log_monitoring(self):
        if self.log_monitor_thread and self.log_monitor_thread.is_alive():
            return

        if not self.pasta_raiz.get() or not os.path.isdir(self.pasta_raiz.get()):
            self.append_text_to_log_area(
                self.app.translator.get("log_warn_invalid_folder", folder=self.pasta_raiz.get()) + "\n")
            return

        self._stop_event.clear()
        self.log_monitor_thread = threading.Thread(
            target=self._log_processing_worker,
            daemon=True,
            name=f"LogWorker-Votemap-{self.nome}"
        )
        self.log_monitor_thread.start()

    def stop_log_monitoring(self, from_tab_closure=False):
        self._stop_event.set()
        if self.log_monitor_thread and self.log_monitor_thread.is_alive():
            if self.log_monitor_thread != threading.current_thread():
                self.log_monitor_thread.join(timeout=1.5)
        self.log_monitor_thread = None

    def restart_log_monitoring(self):
        self.logger.info(f"Votemap [{self.nome}]: Manual log monitor restart triggered.")
        self.stop_log_monitoring()
        self.app.root.after(100, self.start_log_monitoring)

    def _log_processing_worker(self):
        self.logger.info(f"Votemap [{self.nome}]: Log processing worker started.")
        caminho_log_atual = None
        file_handle = None
        vote_pattern, winner_pattern = None, None

        while not self._stop_event.is_set():
            try:
                if vote_pattern is None:
                    vote_pattern = re.compile(self.vote_pattern_var.get())
                    winner_pattern = re.compile(self.winner_pattern_var.get())

                if self._paused:
                    if self._stop_event.wait(0.5): break
                    continue

                log_filename = self.log_filename_var.get()
                pasta_raiz = self.pasta_raiz.get()
                subpasta_recente = self._obter_subpasta_log_mais_recente(pasta_raiz) if pasta_raiz and os.path.isdir(
                    pasta_raiz) else None

                if subpasta_recente:
                    novo_arquivo_log = os.path.join(subpasta_recente, log_filename)
                    if os.path.exists(novo_arquivo_log) and novo_arquivo_log != caminho_log_atual:
                        self.logger.info(f"Votemap [{self.nome}]: New log file detected: {novo_arquivo_log}")
                        if file_handle: file_handle.close()

                        caminho_log_atual = novo_arquivo_log
                        self.append_text_to_log_area_threadsafe(
                            self.app.translator.get("log_monitoring_file", file=caminho_log_atual))
                        file_handle = open(caminho_log_atual, 'r', encoding='latin-1', errors='replace')
                        file_handle.seek(0, os.SEEK_END)
                        self.aguardando_winner = False

                if file_handle:
                    current_filter = self.filtro_var.get().lower()
                    linha = file_handle.readline()
                    if linha:
                        self._process_log_line(linha, current_filter, vote_pattern, winner_pattern)
                        continue
            except re.error as e:
                self.append_text_to_log_area_threadsafe(self.app.translator.get("log_regex_error", error=e) + "\n")
                self.logger.error(f"Votemap [{self.nome}]: Regex compilation failed: {e}. Worker stopping.")
                break
            except ValueError:
                self.logger.warning(
                    f"Votemap [{self.nome}]: ValueError on read, likely file was closed. Rescanning...")
                if file_handle: file_handle.close()
                file_handle = None
                caminho_log_atual = None
                continue
            except Exception as e:
                self.logger.error(f"Votemap [{self.nome}]: Unhandled error in log worker loop: {e}", exc_info=True)
                if file_handle: file_handle.close()
                file_handle = None
                caminho_log_atual = None

            if self._stop_event.wait(0.2):
                break

        if file_handle:
            file_handle.close()
        self.logger.info(f"Votemap [{self.nome}]: Log processing worker stopped.")

    def _process_log_line(self, linha, current_filter, vote_pattern, winner_pattern):
        self.app.process_player_info_line(linha)
        if not current_filter or current_filter in linha.lower():
            self.append_text_to_log_area(linha)

        if vote_pattern.search(linha):
            self.aguardando_winner = True
            self.logger.info(
                f"Votemap [{self.nome}]: 'EndVote' pattern matched. Now waiting for winner. Line: {linha.strip()}")

        if self.aguardando_winner and winner_pattern.search(linha):
            match = winner_pattern.search(linha)
            self.logger.info(f"Votemap [{self.nome}]: 'Winner' pattern matched. Line: {linha.strip()}")
            if match:
                try:
                    indice_vencedor = int(match.group(1))
                    self.logger.info(f"Votemap [{self.nome}]: Successfully extracted winner index: {indice_vencedor}")
                    self.app.root.after(0, self.processar_troca_mapa_logica, indice_vencedor)
                    self.aguardando_winner = False
                except (IndexError, ValueError) as e:
                    self.logger.error(
                        f"Votemap [{self.nome}]: Found winner pattern, but failed to extract index from match '{match.groups()}'. Error: {e}")
                    self.aguardando_winner = False

    def _obter_subpasta_log_mais_recente(self, pasta_raiz_logs):
        if not pasta_raiz_logs or not os.path.isdir(pasta_raiz_logs): return None
        try:
            log_folder_pattern = re.compile(r"^logs_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")
            subpastas = [os.path.join(pasta_raiz_logs, n) for n in os.listdir(pasta_raiz_logs) if
                         os.path.isdir(os.path.join(pasta_raiz_logs, n)) and log_folder_pattern.match(n)]
            return max(subpastas, key=os.path.getmtime) if subpastas else None
        except:
            return None

    def processar_troca_mapa_logica(self, indice_vencedor):
        _ = self.app.translator.get
        self.logger.info(f"Processando troca de mapa para índice: {indice_vencedor}")
        if not self.arquivo_json.get() or not self.arquivo_json_votemap.get():
            self.append_text_to_log_area(_("log_error_jsons_not_configured") + "\n")
            self.logger.error("ERRO: JSONs de servidor ou votemap não configurados para troca de mapa.")
            return
        try:
            with open(self.arquivo_json_votemap.get(), 'r', encoding='utf-8') as f:
                map_list = json.load(f).get("list", [])
            if not map_list:
                self.append_text_to_log_area(_("log_warn_empty_map_list") + "\n")
                self.logger.warning("Lista de mapas do votemap está vazia.")
                return

            novo_scenario_id, nome_mapa = None, "N/A"

            if indice_vencedor == 0 and len(map_list) > 1:
                indice = random.randint(1, len(map_list) - 1)
                novo_scenario_id = map_list[indice]
                if '}' in novo_scenario_id:
                    nome_mapa = novo_scenario_id.split('}', 1)[1]
                else:
                    nome_mapa = novo_scenario_id
                self.append_text_to_log_area(_("log_random_vote", map=nome_mapa) + "\n")
                self.logger.info(f"Voto aleatório selecionou índice {indice}: {nome_mapa}")

            elif 0 < indice_vencedor < len(map_list):
                novo_scenario_id = map_list[indice_vencedor]
                if '}' in novo_scenario_id:
                    nome_mapa = novo_scenario_id.split('}', 1)[1]
                else:
                    nome_mapa = novo_scenario_id
                self.append_text_to_log_area(_("log_winner_map", map=nome_mapa) + "\n")
                self.logger.info(f"Vencedor selecionado índice {indice_vencedor}: {nome_mapa}")

            else:
                self.append_text_to_log_area(_("log_error_invalid_winner_index", index=indice_vencedor) + "\n")
                self.logger.error(
                    f"Índice do vencedor ({indice_vencedor}) é inválido para a lista de mapas de tamanho {len(map_list)}.")
                return

            with open(self.arquivo_json.get(), 'r+', encoding='utf-8') as f:
                server_data = json.load(f)
                server_data.setdefault("game", {})["scenarioId"] = novo_scenario_id
                f.seek(0)
                json.dump(server_data, f, indent=4)
                f.truncate()

            self._display_json_in_widget(self.json_text_area_server, server_data)
            self.append_text_to_log_area(_("log_server_json_updated", map=nome_mapa) + "\n")
            self.logger.info(f"JSON do servidor atualizado para: {nome_mapa} ({novo_scenario_id})")

            if self.auto_restart_var.get() and self.nome_servico.get():
                self.append_text_to_log_area(_("log_auto_restart_starting") + "\n")
                self.logger.info("Iniciando reinício automático do servidor após troca de mapa.")
                threading.Thread(target=self.reiniciar_servidor_worker, daemon=True).start()
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.append_text_to_log_area(_("log_error_map_change", error=e) + "\n")
            self.logger.error(f"Erro de arquivo ou JSON na troca de mapa: {e}", exc_info=True)
        except Exception as e:
            self.append_text_to_log_area(_("log_error_map_change", error=e) + "\n")
            self.logger.error(f"Erro inesperado na troca de mapa: {e}", exc_info=True)

    def reiniciar_servidor_worker(self):
        _ = self.app.translator.get
        nome_servico = self.nome_servico.get()
        if not nome_servico: self.append_text_to_log_area_threadsafe(
            _("log_error_service_not_configured") + "\n"); return
        self.logger.info(f"Iniciando reinício de '{nome_servico}'.")
        success = self._executar_logica_reinicio_servico(nome_servico)
        if self.app.root.winfo_exists():
            if success:
                self.app.show_messagebox_from_thread("success", _("dialog_restart_complete_title", server=self.nome),
                                                     _("dialog_restart_complete_msg", service=nome_servico))
            else:
                self.app.show_messagebox_from_thread("error",
                                                     _("dialog_restart_failed_votemap_title", server=self.nome),
                                                     _("dialog_restart_failed_votemap_msg", service=nome_servico))
            self.update_service_status_display()

    def parar_servico_manual(self):
        _ = self.app.translator.get
        service_name = self.nome_servico.get()
        if not service_name:
            self.app.show_messagebox_from_thread("warning", _("warn_no_service_selected_title"),
                                                 _("warn_no_service_to_stop"))
            return
        threading.Thread(target=self._parar_servico_worker, args=(service_name,), daemon=True).start()

    def iniciar_servico_manual(self):
        _ = self.app.translator.get
        service_name = self.nome_servico.get()
        if not service_name:
            self.app.show_messagebox_from_thread("warning", _("warn_no_service_selected_title"),
                                                 _("warn_no_service_to_start"))
            return
        threading.Thread(target=self._iniciar_servico_worker, args=(service_name,), daemon=True).start()

    def _parar_servico_worker(self, service_name):
        _ = self.app.translator.get
        self.append_text_to_log_area_threadsafe(_("log_manual_stop", service=service_name) + "\n")
        success = self._stop_service(service_name)
        if success:
            self.app.show_messagebox_from_thread("success", _("info_service_stopped_title"),
                                                 _("info_service_stopped_msg", service=service_name))
        else:
            self.app.show_messagebox_from_thread("error", _("error_service_stop_failed_title"),
                                                 _("error_service_stop_failed_msg", service=service_name))
        self.update_service_status_display()

    def _iniciar_servico_worker(self, service_name):
        _ = self.app.translator.get
        self.append_text_to_log_area_threadsafe(_("log_manual_start", service=service_name) + "\n")
        success = self._start_service(service_name)
        if success:
            self.app.show_messagebox_from_thread("success", _("info_service_started_title"),
                                                 _("info_service_started_msg", service=service_name))
        else:
            self.app.show_messagebox_from_thread("error", _("error_service_start_failed_title"),
                                                 _("error_service_start_failed_msg", service=service_name))
        self.update_service_status_display()

    def _stop_service(self, service_name):
        _ = self.app.translator.get
        os_system = platform.system()
        try:
            if os_system == "Windows":
                self.append_text_to_log_area_threadsafe(_("log_executing_sc_stop", service=service_name) + "\n")
                startupinfo = subprocess.STARTUPINFO();
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(["sc", "stop", service_name], check=True, startupinfo=startupinfo, timeout=30)
            elif os_system == "Linux":
                nome_servico_systemd = f"{service_name}.service" if not service_name.endswith(
                    ".service") else service_name
                cmd_prefix = ['sudo'] if os.geteuid() != 0 else []
                self.append_text_to_log_area_threadsafe(
                    _("log_executing_sysd_stop", service=nome_servico_systemd) + "\n")
                subprocess.run(cmd_prefix + ['systemctl', 'stop', nome_servico_systemd], check=True,
                               capture_output=True, timeout=30)
            else:
                return False
            return True
        except Exception as e:
            self.append_text_to_log_area_threadsafe(_("log_stop_error", service=service_name, error=e) + "\n")
            self.logger.error(f"Erro ao parar serviço '{service_name}': {e}", exc_info=True)
            return False

    def _start_service(self, service_name):
        _ = self.app.translator.get
        os_system = platform.system()
        try:
            if os_system == "Windows":
                self.append_text_to_log_area_threadsafe(_("log_executing_sc_start", service=service_name) + "\n")
                startupinfo = subprocess.STARTUPINFO();
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(["sc", "start", service_name], check=True, startupinfo=startupinfo, timeout=30)
            elif os_system == "Linux":
                nome_servico_systemd = f"{service_name}.service" if not service_name.endswith(
                    ".service") else service_name
                cmd_prefix = ['sudo'] if os.geteuid() != 0 else []
                self.append_text_to_log_area_threadsafe(
                    _("log_executing_sysd_start", service=nome_servico_systemd) + "\n")
                subprocess.run(cmd_prefix + ['systemctl', 'start', nome_servico_systemd], check=True,
                               capture_output=True, timeout=30)
            else:
                return False
            return True
        except Exception as e:
            self.append_text_to_log_area_threadsafe(_("log_start_error", service=service_name, error=e) + "\n")
            self.logger.error(f"Erro ao iniciar serviço '{service_name}': {e}", exc_info=True)
            return False

    def _executar_logica_reinicio_servico(self, nome_servico):
        if self._stop_service(nome_servico):
            time.sleep(self.stop_delay_var.get())
            if self._start_service(nome_servico):
                time.sleep(self.start_delay_var.get())
                self._restaurar_json_para_votemap()
                return True
        return False

    def _restaurar_json_para_votemap(self):
        _ = self.app.translator.get
        default_mission = self.default_mission_var.get()
        server_json = self.arquivo_json.get()
        self.append_text_to_log_area_threadsafe(_("log_restoring_json") + "\n")
        if not default_mission or not server_json or not os.path.exists(server_json):
            self.append_text_to_log_area_threadsafe(_("log_warn_json_not_restored") + "\n");
            return
        try:
            with open(server_json, 'r+', encoding='utf-8') as f:
                data = json.load(f)
                data.setdefault("game", {})["scenarioId"] = default_mission
                f.seek(0);
                json.dump(data, f, indent=4);
                f.truncate()
            if self.winfo_exists(): self.app.root.after(0, self._display_json_in_widget, self.json_text_area_server,
                                                        data)
            self.append_text_to_log_area_threadsafe(_("log_json_restored") + "\n")
        except Exception as e:
            self.append_text_to_log_area_threadsafe(_("log_error_restoring_json", error=e) + "\n")
            self.logger.error(f"Erro ao restaurar JSON: {e}", exc_info=True)

    def append_text_to_log_area(self, texto):
        if self.winfo_exists():
            try:
                self.app.root.after(0, self._append_text_to_log_area_gui_thread, texto)
            except:
                pass

    def _append_text_to_log_area_gui_thread(self, texto):
        if self.text_area_log.winfo_exists():
            self.text_area_log.config(state='normal')
            self.text_area_log.insert('end', texto)
            if self.auto_scroll_log_var.get(): self.text_area_log.yview_moveto(1.0)
            self.text_area_log.config(state='disabled')

    def append_text_to_log_area_threadsafe(self, texto):
        self.append_text_to_log_area(texto)

    def limpar_tela_log(self):
        if self.text_area_log.winfo_exists():
            self.text_area_log.config(state='normal')
            self.text_area_log.delete('1.0', 'end')
            self.text_area_log.config(state='disabled')

    def toggle_pausa(self):
        _ = self.app.translator.get
        self._paused = not self._paused
        self.pausar_btn.config(text=_("btn_resume") if self._paused else _("btn_pause"),
                               bootstyle=SUCCESS if self._paused else WARNING)

    def _toggle_log_search_bar(self, event=None, force_hide=False, force_show=False):
        is_visible = self.search_log_frame.winfo_ismapped()
        if force_hide or (is_visible and not force_show):
            self.search_log_frame.pack_forget()
        elif force_show or not is_visible:
            self.search_log_frame.pack(fill='x', before=self.text_area_log, pady=(0, 2), padx=5)
            self.log_search_entry.focus_set()

    def _perform_log_search_internal(self, term, start_pos, forward=True):
        if not term: return None
        self.text_area_log.tag_remove("search_match", "1.0", "end")
        count = tk.IntVar()
        self.text_area_log.config(state="normal")
        pos = self.text_area_log.search(term, start_pos, backwards=not forward, count=count, nocase=True,
                                        stopindex="1.0" if not forward else "end")
        if pos:
            end_pos = f"{pos}+{count.get()}c"
            self.text_area_log.tag_add("search_match", pos, end_pos)
            self.text_area_log.tag_config("search_match", background="yellow", foreground="black")
            self.text_area_log.see(pos)
            self.text_area_log.config(state="disabled")
            return end_pos if forward else pos
        wrap_start = "1.0" if forward else "end"
        pos = self.text_area_log.search(term, wrap_start, backwards=not forward, count=count, nocase=True)
        if pos:
            end_pos = f"{pos}+{count.get()}c"
            self.text_area_log.tag_add("search_match", pos, end_pos)
            self.text_area_log.see(pos)
            self.text_area_log.config(state="disabled")
            return end_pos if forward else pos
        self.text_area_log.config(state="disabled")
        return None

    def _search_log_next(self, event=None):
        current_selection = self.text_area_log.tag_ranges("search_match")
        start_pos = current_selection[1] if current_selection else self.last_search_pos
        next_pos = self._perform_log_search_internal(self.log_search_var.get(), start_pos, True)
        if next_pos: self.last_search_pos = next_pos

    def _search_log_prev(self, event=None):
        current_selection = self.text_area_log.tag_ranges("search_match")
        start_pos = current_selection[0] if current_selection else self.last_search_pos
        prev_pos = self._perform_log_search_internal(self.log_search_var.get(), start_pos, False)
        if prev_pos: self.last_search_pos = prev_pos


# ==============================================================================
# CLASSE UnifiedMultiToolApp - APLICAÇÃO PRINCIPAL UNIFICADA
# ==============================================================================
class UnifiedMultiToolApp:
    def __init__(self, root):
        self.root = root
        self.style = ttk.Style()
        self.config_file = "unified_config.json"
        self.config = self._load_app_config_from_file()
        self._shutting_down = False

        self.translator = I18N()
        self.translator.set_language(self.config.get("language", "pt-br"))
        _ = self.translator.get

        self.root.title(_("app_title"))
        self.root.geometry("1024x768")

        # --- NOVO: Atributos da Central de Notificações ---
        self.notifications_history = deque(maxlen=100)  # Limita a 100 notificações
        self.unread_notifications = tk.IntVar(value=0)
        self.active_toasts = []
        self.collect_player_info_var = tk.BooleanVar(value=self.config.get("collect_player_info", False))
        self.player_db_conn = None
        self.player_db_lock = threading.Lock()
        if self.collect_player_info_var.get():
            self._init_player_info_db()

        try:
            self.style.theme_use(self.config.get("theme", "darkly"))
        except tk.TclError:
            self.style.theme_use("litera")
            self.config["theme"] = "litera"
            app_logger.warning(f"Tema '{self.config.get('theme')}' não encontrado. Usando 'litera'.")

        self.restarter_servidores = []
        self.votemap_servidores = []
        self.config_changed = False
        self._app_stop_event = threading.Event()
        self.tray_icon = None
        self.app_icon_tk = None
        self.original_pil_bg_image = None
        self.bg_photo_image = None
        self.bg_label = None

        self.set_application_icon()
        self._setup_background_image()
        self.create_main_widgets()
        self.create_menu()
        self.create_status_bar()  # Modificado para incluir o sino
        self.update_ui_text()
        self.inicializar_modulos_das_configuracoes()

        if self.bg_label and self.bg_label.winfo_exists(): self.bg_label.lower()

        self.atualizar_logs_sistema_periodicamente()
        self.root.bind("<Configure>", self._on_root_configure)
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray_on_close)

        # NOVO: Trace para atualizar a badge do sino
        self.unread_notifications.trace_add("write", self._update_bell_badge)

        if PYSTRAY_AVAILABLE: self.setup_tray_icon()

    def create_main_widgets(self):
        """Cria os widgets principais da UI que precisam existir antes de tudo."""
        _ = self.translator.get
        self.top_level_notebook = ttk.Notebook(self.root)
        self.top_level_notebook.pack(fill='both', expand=True, padx=5, pady=5)

        self.restarter_frame = ttk.Frame(self.top_level_notebook)
        self.top_level_notebook.add(self.restarter_frame)
        self.restarter_notebook = ttk.Notebook(self.restarter_frame)
        self.restarter_notebook.pack(fill='both', expand=True)
        self.restarter_notebook.bind('<Double-1>', self._on_tab_double_click)

        self.restarter_system_log_frame = ttk.Frame(self.restarter_notebook)
        self.restarter_notebook.add(self.restarter_system_log_frame, text="Log do Sistema")
        self.restarter_system_log_area = ScrolledText(self.restarter_system_log_frame, wrap='word', height=10,
                                                      state='disabled')
        self.restarter_system_log_area.pack(fill='both', expand=True, padx=5, pady=5)

        restarter_log_controls_frame = ttk.Frame(self.restarter_system_log_frame)
        restarter_log_controls_frame.pack(fill='x', padx=5, pady=(0, 5))
        self.restarter_log_autoscroll_var = tk.BooleanVar(value=True)
        self.restarter_autoscroll_check = ttk.Checkbutton(
            restarter_log_controls_frame,
            variable=self.restarter_log_autoscroll_var,
            text=_("chk_system_log_auto_scroll")
        )
        self.restarter_autoscroll_check.pack(side='left')

        self.votemap_frame = ttk.Frame(self.top_level_notebook)
        self.top_level_notebook.add(self.votemap_frame)
        self.votemap_notebook = ttk.Notebook(self.votemap_frame)
        self.votemap_notebook.pack(fill='both', expand=True)
        self.votemap_notebook.bind('<Double-1>', self._on_tab_double_click)

        self.votemap_system_log_frame = ttk.Frame(self.votemap_notebook)
        self.votemap_notebook.add(self.votemap_system_log_frame, text="Log do Sistema")
        self.votemap_system_log_area = ScrolledText(self.votemap_system_log_frame, wrap='word', height=10,
                                                    state='disabled')
        self.votemap_system_log_area.pack(fill='both', expand=True, padx=5, pady=5)

        votemap_log_controls_frame = ttk.Frame(self.votemap_system_log_frame)
        votemap_log_controls_frame.pack(fill='x', padx=5, pady=(0, 5))
        self.votemap_log_autoscroll_var = tk.BooleanVar(value=True)
        self.votemap_autoscroll_check = ttk.Checkbutton(
            votemap_log_controls_frame,
            variable=self.votemap_log_autoscroll_var,
            text=_("chk_system_log_auto_scroll")
        )
        self.votemap_autoscroll_check.pack(side='left')

    def inicializar_modulos_das_configuracoes(self):
        _ = self.translator.get
        restarter_configs = self.config.get("restarter_servers", [])
        if not restarter_configs:
            self.adicionar_restarter_tab(_("default_server_name", count=1))
        else:
            for conf in restarter_configs: self.adicionar_restarter_tab(conf.get("nome"), conf, focus_new_tab=False)
        votemap_configs = self.config.get("votemap_servers", [])
        if not votemap_configs:
            self.adicionar_votemap_tab(_("default_server_name", count=1))
        else:
            for conf in votemap_configs: self.adicionar_votemap_tab(conf.get("nome"), conf, focus_new_tab=False)

    def adicionar_restarter_tab(self, nome_sugerido=None, config=None, focus_new_tab=True):
        _ = self.translator.get
        nome_final = self._get_unique_tab_name(nome_sugerido, [s.nome for s in self.restarter_servidores],
                                               _("default_server_name", count=1).split(' ')[0])
        tab = RestarterTab(self.restarter_notebook, self, nome_final, config)
        self.restarter_servidores.append(tab)
        self.restarter_notebook.add(tab, text=nome_final)
        if focus_new_tab: self.restarter_notebook.select(tab)
        self.mark_config_changed()

    def adicionar_votemap_tab(self, nome_sugerido=None, config=None, focus_new_tab=True):
        _ = self.translator.get
        nome_final = self._get_unique_tab_name(nome_sugerido, [s.nome for s in self.votemap_servidores],
                                               _("default_server_name", count=1).split(' ')[0])
        tab = VotemapTab(self.votemap_notebook, self, nome_final, config)
        self.votemap_servidores.append(tab)
        self.votemap_notebook.add(tab, text=nome_final)
        if focus_new_tab: self.votemap_notebook.select(tab)
        self.mark_config_changed()

    def _get_unique_tab_name(self, sugerido, existentes, base_name="Servidor"):
        if sugerido is None: sugerido = base_name
        final_nome = sugerido
        count = 1
        while final_nome in existentes:
            final_nome = f"{base_name} ({count})"
            count += 1
        return final_nome

    def _get_active_tab_info(self):
        try:
            active_tool_frame = self.top_level_notebook.nametowidget(self.top_level_notebook.select())
            if active_tool_frame == self.restarter_frame:
                notebook, servidores = self.restarter_notebook, self.restarter_servidores
            elif active_tool_frame == self.votemap_frame:
                notebook, servidores = self.votemap_notebook, self.votemap_servidores
            else:
                return None, None, None

            tab_id = notebook.select()
            if not tab_id: return None, None, None  # Se nenhuma sub-aba estiver selecionada
            current_tab = notebook.nametowidget(tab_id)

            if isinstance(current_tab, (RestarterTab, VotemapTab)):
                return notebook, servidores, current_tab
            else:
                return None, None, None
        except (tk.TclError, KeyError):
            return None, None, None

    def remover_servidor_atual(self):
        _ = self.translator.get
        notebook, servidores, current_tab = self._get_active_tab_info()

        if not current_tab:
            self.show_messagebox_from_thread("warning", _("dialog_invalid_action_title"),
                                             _("dialog_invalid_action_msg"))
            return

        try:
            active_top_tab_id = self.top_level_notebook.select()
            tool_name = self.top_level_notebook.tab(active_top_tab_id, "text")
        except tk.TclError:
            tool_name = "desconhecida"

        nome_servidor = current_tab.nome
        if Messagebox.okcancel(_("dialog_remove_server_title", server=nome_servidor),
                               _("dialog_remove_server_msg", server=nome_servidor,
                                 tool=tool_name),
                               parent=self.root,
                               alert=True) == "OK":
            current_tab.stop_log_monitoring(from_tab_closure=True)
            if isinstance(current_tab, RestarterTab): current_tab.stop_scheduler_thread(from_tab_closure=True)
            notebook.forget(current_tab)
            if current_tab in servidores: servidores.remove(current_tab)
            current_tab.destroy()
            self.mark_config_changed()
            self.set_status_from_thread(
                _("status_server_removed", server=nome_servidor, tool=tool_name))

    def rename_current_server(self):
        _ = self.translator.get
        notebook, servidores, current_tab = self._get_active_tab_info()

        if not current_tab:
            self.show_messagebox_from_thread("warning", _("dialog_invalid_action_title"),
                                             _("dialog_invalid_action_msg"))
            return

        self._rename_tab(notebook, servidores, current_tab)

    def _on_tab_double_click(self, event):
        notebook = event.widget
        try:
            tab_index = notebook.index(f"@{event.x},{event.y}")
            tab_id = notebook.tabs()[tab_index]
            tab_widget = notebook.nametowidget(tab_id)

            if notebook == self.restarter_notebook:
                servidores = self.restarter_servidores
            elif notebook == self.votemap_notebook:
                servidores = self.votemap_servidores
            else:
                return

            if isinstance(tab_widget, (RestarterTab, VotemapTab)):
                self._rename_tab(notebook, servidores, tab_widget)
        except tk.TclError:
            pass

    def _rename_tab(self, notebook, servidores_list, tab_to_rename):
        _ = self.translator.get
        old_name = tab_to_rename.nome
        new_name = simpledialog.askstring(
            _("dialog_rename_server_title", server=old_name),
            _("dialog_rename_server_prompt"),
            initialvalue=old_name,
            parent=self.root
        )

        if not new_name or new_name == old_name:
            return

        if not new_name.strip():
            self.show_messagebox_from_thread("error", _("dialog_rename_error_empty_title"),
                                             _("dialog_rename_error_empty_msg"))
            return

        existing_names = [s.nome for s in servidores_list if s is not tab_to_rename]
        if new_name in existing_names:
            self.show_messagebox_from_thread("error", _("dialog_rename_error_duplicate_title"),
                                             _("dialog_rename_error_duplicate_msg", name=new_name))
            return

        tab_to_rename.nome = new_name
        notebook.tab(tab_to_rename, text=new_name)
        self.mark_config_changed()
        self.set_status_from_thread(_("status_server_renamed", name=new_name))
        app_logger.info(f"Servidor '{old_name}' renomeado para '{new_name}'.")

    def _load_app_config_from_file(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                app_logger.error(f"Erro ao carregar '{self.config_file}': {e}")
        return {"theme": "darkly", "language": "pt-br", "collect_player_info": False, "restarter_servers": [], "votemap_servers": []}

    def _save_app_config_to_file(self):
        config_data = {
            "theme": self.style.theme.name,
            "language": self.translator.language,
            "collect_player_info": self.collect_player_info_var.get(),
            "restarter_servers": [s.get_current_config() for s in self.restarter_servidores],
            "votemap_servers": [s.get_current_config() for s in self.votemap_servidores]
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
            self.config_changed = False
            self.file_menu.entryconfigure(self.translator.get("menu_save_config"), state="disabled")
            self.set_status_from_thread(self.translator.get("status_config_saved"))
            app_logger.info("Configuração unificada salva.")
        except Exception as e:
            self.show_messagebox_from_thread("error", self.translator.get("dialog_save_error_title"),
                                             self.translator.get("dialog_save_error_msg", error=e))
            app_logger.error(f"Erro ao salvar configuração: {e}", exc_info=True)

    def create_menu(self):
        self.menubar = ttk.Menu(self.root)
        self.root.config(menu=self.menubar)

    def update_ui_text(self):
        """Atualiza o texto dos menus e widgets principais."""
        _ = self.translator.get
        self.root.title(_("app_title"))

        self.menubar.delete(0, "end")

        self.file_menu = ttk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=_("menu_file"), menu=self.file_menu)
        save_state = "normal" if self.config_changed else "disabled"
        self.file_menu.add_command(label=_("menu_save_config"), command=self._save_app_config_to_file, state=save_state)
        self.file_menu.add_separator()
        self.file_menu.add_command(label=_("menu_exit"), command=self.shutdown_application)

        self.restarter_menu = ttk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=_("menu_restarter"), menu=self.restarter_menu)
        self.restarter_menu.add_command(label=_("menu_add_server"),
                                        command=lambda: self.adicionar_restarter_tab(focus_new_tab=True))
        self.restarter_menu.add_command(label=_("menu_rename_server"), command=self.rename_current_server)
        self.restarter_menu.add_command(label=_("menu_remove_current_server"), command=self.remover_servidor_atual)

        self.votemap_menu = ttk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=_("menu_votemap"), menu=self.votemap_menu)
        self.votemap_menu.add_command(label=_("menu_add_server"),
                                      command=lambda: self.adicionar_votemap_tab(focus_new_tab=True))
        self.votemap_menu.add_command(label=_("menu_rename_server"), command=self.rename_current_server)
        self.votemap_menu.add_command(label=_("menu_remove_current_server"), command=self.remover_servidor_atual)

        tools_menu = ttk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=_("menu_tools"), menu=tools_menu)
        theme_menu = ttk.Menu(tools_menu, tearoff=0)
        tools_menu.add_cascade(label=_("menu_change_theme"), menu=theme_menu)
        self.theme_var = tk.StringVar(value=self.style.theme.name)
        for theme_name in sorted(self.style.theme_names()):
            theme_menu.add_radiobutton(label=theme_name, variable=self.theme_var, command=self.trocar_tema)

        tools_menu.add_checkbutton(
            label=_("menu_collect_player_info"),
            variable=self.collect_player_info_var,
            command=self.toggle_collect_player_info
        )

        lang_menu = ttk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=_("menu_language"), menu=lang_menu)
        self.lang_var = tk.StringVar(value=self.translator.language)
        lang_menu.add_radiobutton(label="Português (Brasil)", variable=self.lang_var, value='pt-br',
                                  command=self.switch_language)
        lang_menu.add_radiobutton(label="English (US)", variable=self.lang_var, value='en-us',
                                  command=self.switch_language)

        help_menu = ttk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=_("menu_help"), menu=help_menu)
        help_menu.add_command(label=_("menu_about"), command=self.show_about)

        self.top_level_notebook.tab(self.restarter_frame, text=_("tab_top_restarter"))
        self.top_level_notebook.tab(self.votemap_frame, text=_("tab_top_votemap"))
        self.restarter_notebook.tab(self.restarter_system_log_frame, text=f"{_('tab_system_log')} (Restarter)")
        self.votemap_notebook.tab(self.votemap_system_log_frame, text=f"{_('tab_system_log')} (Votemap)")
        self.restarter_autoscroll_check.config(text=_('chk_system_log_auto_scroll'))
        self.votemap_autoscroll_check.config(text=_('chk_system_log_auto_scroll'))

        current_status = self.status_label_var.get()
        if current_status == "Pronto." or current_status == "Ready.":
            self.status_label_var.set(_("status_ready"))

    def switch_language(self):
        new_lang = self.lang_var.get()
        if self.translator.language != new_lang:
            self.translator.set_language(new_lang)
            self.update_ui_text()
            for tab in self.restarter_servidores + self.votemap_servidores:
                if tab.winfo_exists():
                    tab.update_ui_text()
            self.mark_config_changed()

    def trocar_tema(self):
        novo_tema = self.theme_var.get()
        try:
            self.style.theme_use(novo_tema)
            for srv_tab in self.restarter_servidores + self.votemap_servidores:
                if srv_tab.winfo_exists(): srv_tab.initialize_from_config_vars()
            self.config["theme"] = novo_tema
            self.mark_config_changed()
        except tk.TclError:
            self.show_messagebox_from_thread("error", self.translator.get("dialog_theme_error_title"),
                                             self.translator.get("dialog_theme_error_msg", theme=novo_tema))

    def show_about(self):
        _ = self.translator.get
        Messagebox.show_info(title=_("about_title"), message=_("about_message"), parent=self.root)

    def shutdown_application(self):
        if self._shutting_down:
            return
        self._shutting_down = True
        app_logger.info("Iniciando processo de encerramento...")
        self._app_stop_event.set()
        for tab in self.restarter_servidores + self.votemap_servidores:
            tab.stop_log_monitoring(from_tab_closure=True)
            if isinstance(tab, RestarterTab): tab.stop_scheduler_thread(from_tab_closure=True)
        if self.config_changed: self._save_app_config_to_file()
        if self.player_db_conn:
            try:
                self.player_db_conn.close()
            except Exception:
                pass
            self.player_db_conn = None
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception as e:
                app_logger.debug(f"Erro (benigno?) ao parar tray icon: {e}")
        try:
            if self.root.winfo_exists():
                self.root.destroy()
        except tk.TclError:
            pass
        app_logger.info("Aplicação encerrada.")

    def atualizar_logs_sistema_periodicamente(self):
        if self._app_stop_event.is_set(): return
        self._update_single_log_area(LOG_FILENAME_RESTARTER, self.restarter_system_log_area,
                                     self.restarter_log_autoscroll_var)
        self._update_single_log_area(LOG_FILENAME_VOTEMAP, self.votemap_system_log_area,
                                     self.votemap_log_autoscroll_var)
        self.root.after(3000, self.atualizar_logs_sistema_periodicamente)

    def _update_single_log_area(self, log_file, text_widget, autoscroll_var):
        if self._shutting_down or not self.root.winfo_exists() or not text_widget.winfo_exists(): return
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                current_content = text_widget.get('1.0', 'end-1c')
                if content != current_content:
                    text_widget.config(state='normal')
                    text_widget.delete('1.0', 'end')
                    text_widget.insert('end', content)
                    if autoscroll_var.get(): text_widget.yview_moveto(1.0)
                    text_widget.config(state='disabled')
        except (tk.TclError, Exception):
            pass

    def iniciar_selecao_servico_para_aba(self, tab_instance, os_type):
        _ = self.translator.get
        worker = None
        if os_type == "windows":
            if not PYWIN32_AVAILABLE:
                self.show_messagebox_from_thread("error", _("dialog_missing_component_title"),
                                                 _("dialog_missing_pywin32"))
                return
            worker = self._obter_servicos_worker_win
        elif os_type == "linux":
            if not SYSTEMCTL_AVAILABLE:
                self.show_messagebox_from_thread("error", _("dialog_missing_component_title"),
                                                 _("dialog_missing_systemctl"))
                return
            worker = self._obter_servicos_worker_linux
        else:
            return
        progress_win, _ = self._show_progress_dialog(_("dialog_loading_services_title", os=os_type.capitalize()),
                                                     _("dialog_loading_services_msg"))
        threading.Thread(target=worker, args=(progress_win, tab_instance), daemon=True).start()

    def _obter_servicos_worker_win(self, progress_win, tab_instance):
        _ = self.translator.get
        initialized_com = False
        try:
            pythoncom.CoInitialize()
            initialized_com = True
            wmi = win32com.client.GetObject('winmgmts:')
            services = sorted([s.Name for s in wmi.InstancesOf('Win32_Service') if s.Name and s.AcceptStop])
            if not self._shutting_down and self.root.winfo_exists():
                self.root.after(0, self._mostrar_dialogo_selecao_servico, services, progress_win, tab_instance,
                                "Windows")
        except Exception as e:
            app_logger.error(f"Erro ao listar serviços Win: {e}", exc_info=True)
            if not self._shutting_down:
                self.show_messagebox_from_thread("error", _("dialog_wmi_error_title"),
                                                 _("dialog_wmi_error_msg", error=e))
        finally:
            if progress_win.winfo_exists(): self.root.after(0, progress_win.destroy)
            if initialized_com: pythoncom.CoUninitialize()

    def _obter_servicos_worker_linux(self, progress_win, tab_instance):
        _ = self.translator.get
        try:
            cmd_prefix = ['sudo'] if os.geteuid() != 0 else []
            cmd = cmd_prefix + ['systemctl', 'list-units', '--type=service', '--all', '--no-legend', '--no-pager']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=15)
            services_raw = [line.split()[0] for line in result.stdout.strip().split('\n') if line]
            services = sorted(list(set([s.replace('.service', '') for s in services_raw])))
            if not self._shutting_down and self.root.winfo_exists():
                self.root.after(0, self._mostrar_dialogo_selecao_servico, services, progress_win, tab_instance, "Linux")
        except Exception as e:
            err_details = e.stderr if hasattr(e, 'stderr') else str(e)
            app_logger.error(f"Erro ao listar serviços Linux: {err_details}", exc_info=True)
            if not self._shutting_down:
                self.show_messagebox_from_thread("error", _("dialog_systemctl_error_title"),
                                                 _("dialog_systemctl_error_msg", error=err_details))
        finally:
            if progress_win.winfo_exists(): self.root.after(0, progress_win.destroy)

    def _mostrar_dialogo_selecao_servico(self, service_list, progress_win, tab_instance, os_type):
        _ = self.translator.get
        if progress_win.winfo_exists(): progress_win.destroy()
        if not service_list:
            self.show_messagebox_from_thread("info", _("dialog_no_services_found_title"),
                                             _("dialog_no_services_found_msg", os=os_type))
            return
        dialog = ttk.Toplevel(self.root)
        dialog.title(_("dialog_select_service_title", server=tab_instance.nome))
        dialog.geometry("500x450");
        dialog.transient(self.root);
        dialog.grab_set()
        search_var = tk.StringVar()
        search_entry = ttk.Entry(dialog, textvariable=search_var)
        search_entry.pack(fill='x', padx=10, pady=5)
        treeview = ttk.Treeview(dialog, columns=("name",), show="headings", selectmode="browse")
        treeview.heading("name", text=_("dialog_service_name_header", os=os_type))
        treeview.pack(fill='both', expand=True, padx=10, pady=5)

        def _populate(query=""):
            treeview.delete(*treeview.get_children())
            for name in (s for s in service_list if query.lower() in s.lower()): treeview.insert("", "end",
                                                                                                 values=(name,))

        _populate()
        search_entry.bind("<KeyRelease>", lambda e: _populate(search_var.get()))

        def on_confirm():
            if treeview.selection():
                tab_instance.set_selected_service(treeview.item(treeview.selection()[0], "values")[0])
                dialog.destroy()

        treeview.bind("<Double-1>", lambda e: on_confirm())
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=_("btn_confirm"), command=on_confirm, bootstyle=SUCCESS).pack(side='left', padx=5)
        ttk.Button(btn_frame, text=_("btn_cancel"), command=dialog.destroy, bootstyle=DANGER).pack(side='left', padx=5)
        dialog.wait_window()

    def mark_config_changed(self):
        if not self.config_changed:
            self.config_changed = True
            if hasattr(self, 'file_menu'):
                self.file_menu.entryconfigure(self.translator.get("menu_save_config"), state="normal")

    def _init_player_info_db(self):
        db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'players_info.db')
        try:
            self.player_db_conn = sqlite3.connect(db_path, check_same_thread=False)
            with self.player_db_conn:
                self.player_db_conn.execute(
                    'CREATE TABLE IF NOT EXISTS players (Player_Nickname TEXT PRIMARY KEY, Bohemia_ID TEXT)'
                )
        except Exception as e:
            app_logger.error(f"Erro ao inicializar banco de jogadores: {e}", exc_info=True)

    def toggle_collect_player_info(self):
        if self.collect_player_info_var.get():
            if not self.player_db_conn:
                self._init_player_info_db()
        else:
            if self.player_db_conn:
                try:
                    self.player_db_conn.close()
                except Exception:
                    pass
                self.player_db_conn = None
        self.mark_config_changed()

    def process_player_info_line(self, line):
        if not self.collect_player_info_var.get():
            return
        if not self.player_db_conn:
            self._init_player_info_db()
        match = re.search(r'"(?P<nick>[^"]+)".*?(?P<id>\d+)', line)
        if match and self.player_db_conn:
            nick = match.group('nick')
            bid = match.group('id')
            try:
                with self.player_db_lock:
                    self.player_db_conn.execute(
                        'INSERT OR IGNORE INTO players (Player_Nickname, Bohemia_ID) VALUES (?, ?)',
                        (nick, bid)
                    )
                    self.player_db_conn.commit()
            except Exception as e:
                app_logger.error(f"Erro ao inserir jogador: {e}", exc_info=True)

    def create_status_bar(self):
        self.status_bar_frame = ttk.Frame(self.root)
        self.status_bar_frame.pack(side='bottom', fill='x', pady=(0, 2), padx=2)
        ttk.Separator(self.status_bar_frame).pack(side='top', fill='x')

        self.status_label_var = tk.StringVar(value=self.translator.get("status_ready"))
        ttk.Label(self.status_bar_frame, textvariable=self.status_label_var, anchor='w').pack(side='left', fill='x',
                                                                                              expand=True, padx=5)

        # --- NOVO: Botão de sino e badge para notificações ---
        self.bell_frame = ttk.Frame(self.status_bar_frame)
        self.bell_frame.pack(side='right', padx=5)

        self.bell_button = ttk.Button(self.bell_frame, text='🔔', command=self.show_notification_center,
                                      bootstyle='link')
        self.bell_button.pack()
        ToolTip(self.bell_button, self.translator.get("notification_center_title"))

        self.bell_badge_label = ttk.Label(self.bell_frame, textvariable=self.unread_notifications,
                                          bootstyle="danger-inverse",
                                          font="-size 7 -weight bold", padding=(2, 0))
        # A visibilidade da badge é controlada em _update_bell_badge

    def _update_bell_badge(self, *args):
        """Mostra ou esconde a badge de notificações não lidas."""
        count = self.unread_notifications.get()
        if count > 0:
            self.bell_badge_label.place(in_=self.bell_button, relx=1.0, rely=0.0, anchor='ne')
        else:
            self.bell_badge_label.place_forget()

    def set_status_from_thread(self, message):
        if not self._shutting_down and hasattr(self, 'root') and self.root.winfo_exists() and hasattr(self,
                                                                                                      'status_label_var'):
            self.root.after(0, lambda: self.status_label_var.set(str(message)[:250]))

    def show_messagebox_from_thread(self, boxtype, title, message):
        """
        Mantém o nome para compatibilidade com o código antigo, mas agora
        chama o novo sistema de notificações toast.
        Caixas de diálogo que exigem resposta (como ok/cancel) ainda usarão Messagebox diretamente.
        """
        # Apenas notificações informativas viram toasts.
        if boxtype in ['info', 'success', 'warning', 'error']:
            if not self._shutting_down and self.root.winfo_exists():
                self.root.after(0, self._create_toast_notification, boxtype, title, message)
        else:  # Fallback para caixas de diálogo interativas (se houver)
            if not self._shutting_down and self.root.winfo_exists():
                parent = self.root.focus_get() if isinstance(self.root.focus_get(), tk.Toplevel) else self.root
                self.root.after(0,
                                lambda: getattr(Messagebox, f'show_{boxtype}')(message, title, parent=parent,
                                                                               alert=True))

    def _create_toast_notification(self, boxtype, title, message, duration=5):
        """Cria e gerencia um toast de notificação."""
        self.notifications_history.appendleft((datetime.now(), boxtype, title, message))
        self.unread_notifications.set(self.unread_notifications.get() + 1)

        toast = NotificationToast(self, title, message, boxtype, duration)
        self.active_toasts.append(toast)
        self._reposition_toasts()

    def on_toast_closed(self, toast_instance):
        """Callback chamado quando um toast é fechado."""
        if toast_instance in self.active_toasts:
            self.active_toasts.remove(toast_instance)
        self._reposition_toasts()

    def _reposition_toasts(self):
        """Posiciona todos os toasts ativos para que não se sobreponham."""
        if not self.root.winfo_exists(): return

        screen_w = self.root.winfo_screenwidth()
        margin_x = 10
        margin_y = 10
        spacing = 5

        current_y = self.root.winfo_y() + self.root.winfo_height() - margin_y

        for toast in reversed(self.active_toasts):
            if not toast.winfo_exists(): continue
            toast_height = toast.winfo_height()
            toast_width = 400  # Largura fixa para consistência

            y_pos = current_y - toast_height
            x_pos = screen_w - toast_width - margin_x

            toast.geometry(f"{toast_width}x{toast_height}+{x_pos}+{y_pos}")
            current_y = y_pos - spacing

    def show_notification_center(self):
        _ = self.translator.get
        self.unread_notifications.set(0)

        center_win = ttk.Toplevel(self.root)
        center_win.title(_("notification_center_title"))
        center_win.geometry("800x500")
        center_win.transient(self.root)
        center_win.grab_set()

        top_frame = ttk.Frame(center_win)
        top_frame.pack(side='top', fill='x', padx=10, pady=5)

        ttk.Label(top_frame, text=_("notification_center_title"), font=("-size 12 -weight bold")).pack(side='left')

        tree_frame = ttk.Frame(center_win)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        cols = ('time', 'type', 'title', 'message')
        tree = ttk.Treeview(tree_frame, columns=cols, show='headings')

        col_widths = {'time': 140, 'type': 80, 'title': 150, 'message': 400}
        for col, width in col_widths.items():
            tree.heading(col, text=_(f"col_{col}"))
            tree.column(col, width=width, anchor='w')

        tree.tag_configure('info', background=self.style.colors.get('info'))
        tree.tag_configure('success', background=self.style.colors.get('success'))
        tree.tag_configure('warning', background=self.style.colors.get('warning'))
        tree.tag_configure('error', background=self.style.colors.get('danger'))

        def populate_tree():
            for i in tree.get_children(): tree.delete(i)
            if not self.notifications_history:
                # Adiciona uma mensagem se não houver notificações
                tree.insert('', 'end', values=('', '', '', _('no_notifications')))
            else:
                for item in self.notifications_history:
                    timestamp, boxtype, title, message = item
                    formatted_time = timestamp.strftime('%d/%m/%Y %H:%M:%S')
                    tree.insert('', 'end', values=(formatted_time, boxtype.capitalize(), title, message),
                                tags=(boxtype,))

        populate_tree()

        def clear_history():
            self.notifications_history.clear()
            populate_tree()
            self.show_messagebox_from_thread('info', _('notification_center_title'), _('notification_cleared'))

        ttk.Button(top_frame, text=_("clear_notifications"), command=clear_history, bootstyle='danger-outline').pack(
            side='right')

        tree.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.configure(yscrollcommand=scrollbar.set)

        center_win.wait_window()

    def set_application_icon(self):
        if not os.path.exists(ICON_PATH):
            app_logger.warning(f"Arquivo de ícone não encontrado em: {ICON_PATH}")
            return
        try:
            if PIL_AVAILABLE:
                img = Image.open(ICON_PATH)
                self.app_icon_tk = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, self.app_icon_tk)
                app_logger.info(f"Ícone '{ICON_PATH}' carregado com sucesso via PIL/ImageTk.")
            elif platform.system() == "Windows":
                self.root.iconbitmap(default=ICON_PATH)
                app_logger.info(f"Ícone '{ICON_PATH}' carregado com sucesso via iconbitmap (somente Windows).")
        except Exception as e:
            app_logger.error(f"Falha ao definir o ícone da aplicação de '{ICON_PATH}': {e}", exc_info=True)
            if platform.system() == "Windows":
                try:
                    self.root.iconbitmap(default=ICON_PATH)
                    app_logger.info("Ícone carregado com sucesso via método de fallback iconbitmap.")
                except Exception as e_fallback:
                    app_logger.error(f"Método de fallback iconbitmap também falhou: {e_fallback}", exc_info=True)

    def _setup_background_image(self):
        if not (PIL_AVAILABLE and os.path.exists(BACKGROUND_IMAGE_PATH)):
            if not PIL_AVAILABLE:
                app_logger.warning("Pillow não está instalado, imagem de fundo desabilitada.")
            else:
                app_logger.warning(f"Arquivo de imagem de fundo não encontrado: {BACKGROUND_IMAGE_PATH}")
            return
        try:
            self.original_pil_bg_image = Image.open(BACKGROUND_IMAGE_PATH).convert("RGBA")
            self.bg_label = ttk.Label(self.root)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            self.root.update_idletasks()
            self._resize_background_image(self.root.winfo_width(), self.root.winfo_height())
        except Exception as e:
            app_logger.error(f"Erro ao carregar imagem de fundo: {e}", exc_info=True)
            self.original_pil_bg_image = None;
            self.bg_label = None

    def _on_root_configure(self, event):
        if event.widget == self.root and self.original_pil_bg_image and not self._shutting_down:
            self._resize_background_image(event.width, event.height)

    def _resize_background_image(self, width, height):
        if self._shutting_down or not self.bg_label or not self.bg_label.winfo_exists(): return
        if not self.original_pil_bg_image or width <= 1 or height <= 1: return
        img_copy = self.original_pil_bg_image.copy()
        if 0.0 <= BACKGROUND_ALPHA_MULTIPLIER < 1.0:
            try:
                alpha = img_copy.split()[3]
                alpha = alpha.point(lambda p: int(p * BACKGROUND_ALPHA_MULTIPLIER))
                img_copy.putalpha(alpha)
            except IndexError:
                pass
            except Exception as e:
                app_logger.warning(f"Não foi possível aplicar alfa na imagem: {e}")
        scale_w = width / img_copy.width;
        scale_h = height / img_copy.height
        scale = max(scale_w, scale_h)
        final_w, final_h = int(img_copy.width * scale), int(img_copy.height * scale)
        try:
            resized_pil_img = img_copy.resize((final_w, final_h), Image.Resampling.LANCZOS)
            left, top = (resized_pil_img.width - width) / 2, (resized_pil_img.height - height) / 2
            right, bottom = (resized_pil_img.width + width) / 2, (resized_pil_img.height + height) / 2
            cropped_img = resized_pil_img.crop((left, top, right, bottom))
            self.bg_photo_image = ImageTk.PhotoImage(cropped_img)
            self.bg_label.configure(image=self.bg_photo_image)
        except Exception as e:
            if not self._shutting_down: app_logger.error(f"Erro ao redimensionar imagem de fundo: {e}", exc_info=True)

    def _create_tray_image(self):
        if PIL_AVAILABLE:
            try:
                if os.path.exists(ICON_PATH): return Image.open(ICON_PATH)
                image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
                draw = ImageDraw.Draw(image)
                draw.ellipse((5, 5, 59, 59), fill='skyblue', outline='blue');
                draw.text((20, 20), "MT", fill="navy")
                return image
            except Exception as e:
                app_logger.error(f"Erro ao criar imagem da bandeja: {e}")
        return None

    def setup_tray_icon(self):
        if not PYSTRAY_AVAILABLE: return
        image = self._create_tray_image()
        if not image: return
        menu_items = [pystray.MenuItem('Mostrar', self.show_from_tray, default=True),
                      pystray.MenuItem('Sair', self.shutdown_application_from_tray)]
        try:
            self.tray_icon = pystray.Icon("UnifiedTool", image, "PQDT_Raphael ArmaServerToolBox", tuple(menu_items))
            threading.Thread(target=self.tray_icon.run, daemon=True, name="TrayIconThread").start()
        except Exception as e:
            app_logger.error(f"Erro ao configurar ícone da bandeja: {e}", exc_info=True)

    def show_from_tray(self, icon=None, item=None):
        if not self._shutting_down and self.root.winfo_exists():
            self.root.after(0, self.root.deiconify)
            self.root.after(100, self.root.lift)

    def minimize_to_tray_on_close(self, event=None):
        if self.tray_icon and self.tray_icon.visible:
            self.root.withdraw()
        else:
            self.shutdown_application()

    def shutdown_application_from_tray(self, icon=None, item=None):
        self.shutdown_application()

    def _show_progress_dialog(self, title, message):
        progress_win = ttk.Toplevel(self.root)
        progress_win.title(title);
        progress_win.geometry("300x100");
        progress_win.resizable(False, False)
        progress_win.transient(self.root);
        progress_win.grab_set();
        progress_win.protocol("WM_DELETE_WINDOW", lambda: None)
        ttk.Label(progress_win, text=message).pack(pady=10)
        pb = ttk.Progressbar(progress_win, mode='indeterminate', length=280)
        pb.pack(pady=10);
        pb.start(10)
        progress_win.update_idletasks()
        try:
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (progress_win.winfo_width() // 2)
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (progress_win.winfo_height() // 2)
            progress_win.geometry(f'+{int(x)}+{int(y)}')
        except:
            pass
        return progress_win, pb


# ==============================================================================
# BLOCO DE EXECUÇÃO PRINCIPAL
# ==============================================================================
def handle_unhandled_thread_exception(args):
    exc_info = (args.exc_type, args.exc_value, args.exc_traceback)
    restarter_logger.critical("EXCEÇÃO NÃO TRATADA EM THREAD:", exc_info=exc_info)
    votemap_logger.critical("EXCEÇÃO NÃO TRATADA EM THREAD:", exc_info=exc_info)
    app_logger.critical(f"EXCEÇÃO NÃO TRATADA NA THREAD '{args.thread.name}':", exc_info=exc_info)


def main():
    threading.excepthook = handle_unhandled_thread_exception
    if platform.system() == "Linux" and os.geteuid() != 0:
        print(
            "AVISO: Para gerenciar serviços no Linux (iniciar/parar), execute como root (ex: sudo python3 seu_script.py).")
        app_logger.warning("Executando como não-root no Linux. Funções de serviço podem falhar.")
    root_window = ttk.Window()
    app = None
    try:
        app = UnifiedMultiToolApp(root_window)
        root_window.mainloop()
    except KeyboardInterrupt:
        if app: app_logger.info("Interrupção por teclado. Encerrando...")
    except Exception as e_main:
        app_logger.critical(f"Erro fatal no loop principal: {e_main}", exc_info=True)
    finally:
        if app and not app._shutting_down:
            app.shutdown_application()
        elif not app:
            app_logger.info("Aplicação finalizada.")


if __name__ == '__main__':
    main()
