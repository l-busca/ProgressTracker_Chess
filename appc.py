import sys
import requests
import time
from datetime import datetime
import math
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QHeaderView, QPushButton, QTabWidget, QCheckBox
)
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# Ton pseudo chess.com
username = 'blondletter'  # Changez ce nom pour utiliser un autre utilisateur

# Mode de jeu (blitz, rapid, bullet, etc.)
game_mode = 'rapid'  # Vous pouvez changer ce mode selon vos besoins

# Type de rating correspondant
rating_type = f'chess_{game_mode}'

# Plage de dates (format 'dd/mm/yyyy')
start_date_str = ''  # Exemple : '01/03/2024'
end_date_str = ''    # Exemple : '30/04/2024'

# Filtrer les parties classées ou non classées
# Options:
# - None : inclure toutes les parties
# - True : inclure uniquement les parties classées (compétitives)
# - False : inclure uniquement les parties non classées (amicales)
filter_rated = True  # Changez cette valeur selon vos besoins

# Conversion des dates en objets datetime
if start_date_str:
    try:
        start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
    except ValueError:
        print(f"Date de début invalide : {start_date_str}. Utilisation de toutes les données disponibles.")
        start_date = None
else:
    start_date = None

if end_date_str:
    try:
        end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
        # Ajouter 1 jour pour inclure la date de fin dans le filtrage
        end_date = end_date.replace(hour=23, minute=59, second=59)
    except ValueError:
        print(f"Date de fin invalide : {end_date_str}. Utilisation de toutes les données disponibles.")
        end_date = None
else:
    end_date = None

# Ajouter un User-Agent à la requête
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

# Définir le dossier de cache et la durée d'expiration
CACHE_DIR = os.path.join('cache', username.lower(), game_mode)
CACHE_EXPIRATION = 24 * 3600  # 24 heures en secondes

# Assurez-vous que le dossier de cache existe
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Fonction pour récupérer les statistiques d'un adversaire avec cache
def get_adversary_stats(adversaire):
    cache_file = os.path.join(CACHE_DIR, f"{adversaire.lower()}.json")

    # Vérifier si le fichier de cache existe
    if os.path.exists(cache_file):
        # Lire le fichier de cache
        with open(cache_file, 'r') as f:
            data = json.load(f)
        # Vérifier si le cache est expiré
        cache_time = data.get('timestamp')
        if cache_time and time.time() - cache_time < CACHE_EXPIRATION:
            # Le cache est valide
            adversaire_elo_actuel_int = data.get('adversaire_elo_actuel_int')
            return adversaire_elo_actuel_int
        else:
            # Le cache est expiré, supprimer le fichier
            os.remove(cache_file)

    # Cache manquant ou expiré, faire la requête API
    stats_url = f'https://api.chess.com/pub/player/{adversaire}/stats'
    stats_response = requests.get(stats_url, headers=headers)

    if stats_response.status_code == 200:
        stats = stats_response.json()
        adversaire_elo_actuel = stats.get(rating_type, {}).get('last', {}).get('rating', None)
    else:
        adversaire_elo_actuel = None

    try:
        adversaire_elo_actuel_int = int(adversaire_elo_actuel)
    except (ValueError, TypeError):
        adversaire_elo_actuel_int = None

    # Enregistrer dans le cache
    data = {
        'timestamp': time.time(),
        'adversaire_elo_actuel_int': adversaire_elo_actuel_int
    }

    # S'assurer que le dossier de cache existe
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    with open(cache_file, 'w') as f:
        json.dump(data, f)

    return adversaire_elo_actuel_int

# Fonction pour récupérer les données
def fetch_data():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Début de la récupération des données")
    games_url = f'https://api.chess.com/pub/player/{username}/games/archives'
    archives_response = requests.get(games_url, headers=headers)

    if archives_response.status_code == 200:
        archives = archives_response.json()['archives']
        adversaires_data = []
        unique_adversaries = {}  # Dictionnaire pour stocker les adversaires uniques
        user_elo_history = []  # Liste pour stocker l'historique de l'Elo du joueur

        for archive_url in archives:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Récupération des parties depuis l'archive : {archive_url}")
            games_response = requests.get(archive_url, headers=headers)

            if games_response.status_code == 200:
                games = games_response.json().get('games', [])

                for game in games:
                    # Filtrer par mode de jeu
                    if game['time_class'] != game_mode:
                        continue

                    # Filtrer par type de partie (classée ou non classée)
                    if filter_rated is not None:
                        if game.get('rated', False) != filter_rated:
                            continue

                    white_player = game['white']['username']
                    black_player = game['black']['username']
                    white_elo = game['white']['rating']
                    black_elo = game['black']['rating']
                    date_timestamp = game['end_time']

                    # Convertir le timestamp en objet datetime
                    date_played = datetime.fromtimestamp(date_timestamp)

                    # Filtrer par date si une plage est spécifiée
                    if start_date and date_played < start_date:
                        continue
                    if end_date and date_played > end_date:
                        continue

                    # Déterminer la couleur du joueur et l'adversaire
                    if white_player.lower() == username.lower():
                        adversaire = black_player
                        adversaire_elo_initial = black_elo
                        player_elo_initial = white_elo
                        user_color = 'white'
                        user_result = game['white'].get('result', '')
                    elif black_player.lower() == username.lower():
                        adversaire = white_player
                        adversaire_elo_initial = white_elo
                        player_elo_initial = black_elo
                        user_color = 'black'
                        user_result = game['black'].get('result', '')
                    else:
                        continue

                    if adversaire.lower() == username.lower():
                        continue

                    # Ajouter l'Elo du joueur à l'historique
                    user_elo_history.append((date_played, player_elo_initial))

                    # Récupérer l'Elo actuel de l'adversaire avec le cache
                    if adversaire.lower() not in unique_adversaries:
                        adversaire_elo_actuel_int = get_adversary_stats(adversaire)
                        unique_adversaries[adversaire.lower()] = adversaire_elo_actuel_int
                    else:
                        adversaire_elo_actuel_int = unique_adversaries[adversaire.lower()]

                    try:
                        adversaire_elo_initial_int = int(adversaire_elo_initial)
                        progression = adversaire_elo_actuel_int - adversaire_elo_initial_int if adversaire_elo_actuel_int is not None else 0
                    except ValueError:
                        continue

                    # Déterminer le résultat de la partie
                    if user_result == 'win':
                        result_symbol = 'W'  # Victoire
                    elif user_result in ['checkmated', 'timeout', 'resigned', 'lose']:
                        result_symbol = 'L'  # Défaite
                    elif user_result in ['stalemate', 'agreed', 'repetition', 'timevsinsufficient', 'insufficient', '50move', 'draw']:
                        result_symbol = 'D'  # Match nul
                    else:
                        result_symbol = '?'  # Résultat indéterminé

                    # Déterminer le symbole de la couleur jouée
                    color_symbol = 'B' if user_color == 'white' else 'N'

                    # Calcul du score de progression P
                    E_initial = adversaire_elo_initial_int
                    E_final = adversaire_elo_actuel_int if adversaire_elo_actuel_int is not None else E_initial
                    N_parties = 1  # Puisque chaque ligne représente une partie
                    months = 1  # Nous considérons que la progression se fait sur 1 mois pour chaque partie

                    if E_initial == 0 or E_final == 0:
                        P = 0
                    else:
                        P = (math.log2(E_final / E_initial)) * (12 / months) * (1 + (1 / N_parties))

                    # Arrondir P à deux décimales
                    P = round(P, 2)

                    adversaires_data.append({
                        'note_progression': P,
                        'date_played': date_played,
                        'adversaire': adversaire,
                        'adversaire_elo_initial': adversaire_elo_initial_int,
                        'player_elo_initial': player_elo_initial,
                        'progression': progression,
                        'adversaire_elo_actuel': adversaire_elo_actuel_int if adversaire_elo_actuel_int is not None else 'Inconnu',
                        'color_symbol': color_symbol,
                        'result_symbol': result_symbol
                    })
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Récupération des données terminée")
        return adversaires_data, unique_adversaries, user_elo_history
    else:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Échec de la requête : {archives_response.status_code}")
        return [], {}, []

# Sous-classe pour les éléments numériques
class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, value):
        super().__init__(str(value))
        self.value = value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self.value < other.value
        else:
            return QTableWidgetItem.__lt__(self, other)

# Sous-classe pour les dates
class DateTableWidgetItem(QTableWidgetItem):
    def __init__(self, date_value):
        super().__init__(date_value.strftime('%d/%m/%Y'))
        self.date_value = date_value

    def __lt__(self, other):
        if isinstance(other, DateTableWidgetItem):
            return self.date_value < other.date_value
        else:
            return QTableWidgetItem.__lt__(self, other)

# Classe pour le nouvel histogramme des Elos actuels des adversaires
class EloHistogram(QWidget):
    def __init__(self, adversaries_elo, parent_app):
        super().__init__()
        self.adversaries_elo_original = adversaries_elo.copy()  # Faire une copie pour éviter les modifications
        self.parent_app = parent_app
        self.show_user = True  # Par défaut, afficher l'Elo de l'utilisateur

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Ajouter le graphique
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Ajouter une case à cocher pour afficher/masquer l'Elo de l'utilisateur
        self.checkbox = QCheckBox("Afficher mon Elo")
        self.checkbox.setChecked(True)
        self.checkbox.stateChanged.connect(self.update_graph)
        layout.addWidget(self.checkbox)

        self.plot_graph()

    def plot_graph(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Créer une copie locale du dictionnaire pour éviter les modifications
        adversaries_elo_copy = self.adversaries_elo_original.copy()

        # Données des adversaires
        data_pairs = [(adv, elo) for adv, elo in adversaries_elo_copy.items() if elo is not None]
        data_pairs.sort(key=lambda x: x[1])  # Tri par Elo ascendant
        adversaires_sorted, elos_sorted = zip(*data_pairs) if data_pairs else ([], [])

        # Convertir en listes pour pouvoir les modifier
        adversaires_sorted = list(adversaires_sorted)
        elos_sorted = list(elos_sorted)
        colors = ['blue'] * len(adversaires_sorted)

        # Afficher l'Elo de l'utilisateur si coché
        if self.checkbox.isChecked():
            # Récupérer l'Elo actuel de l'utilisateur
            user_stats_url = f'https://api.chess.com/pub/player/{username}/stats'
            user_stats_response = requests.get(user_stats_url, headers=headers)
            if user_stats_response.status_code == 200:
                user_stats = user_stats_response.json()
                user_elo_actuel = user_stats.get(rating_type, {}).get('last', {}).get('rating', None)
            else:
                user_elo_actuel = None

            if user_elo_actuel is not None:
                # Trouver la position pour insérer l'utilisateur
                inserted = False
                for i, elo in enumerate(elos_sorted):
                    if user_elo_actuel <= elo:
                        adversaires_sorted.insert(i, username)
                        elos_sorted.insert(i, user_elo_actuel)
                        colors.insert(i, 'gold')
                        inserted = True
                        user_index = i
                        break
                if not inserted:
                    adversaires_sorted.append(username)
                    elos_sorted.append(user_elo_actuel)
                    colors.append('gold')
                    user_index = len(elos_sorted) - 1
            else:
                # Si l'Elo de l'utilisateur n'est pas disponible, ne rien faire
                user_index = None
        else:
            user_index = None

        # Recréer l'histogramme avec les données mises à jour
        ax.bar(adversaires_sorted, elos_sorted, color=colors)

        # Ajouter une flèche pour indiquer la position de l'utilisateur
        if user_index is not None:
            ax.annotate(
                'Vous êtes ici',
                xy=(user_index, elos_sorted[user_index]),
                xytext=(user_index, max(elos_sorted) * 1.05),
                arrowprops=dict(facecolor='red', shrink=0.05, width=2, headwidth=8),
                ha='center',
                color='red',
                fontsize=12
            )

        # Personnaliser le graphique
        ax.set_xlabel('Joueurs')
        ax.set_ylabel('Elo actuel')
        ax.set_title('Elo actuel des adversaires')
        ax.tick_params(axis='x', rotation=90)
        plt.tight_layout()

        # Ajuster les couleurs pour le mode nuit
        if self.parent_app.is_dark_mode:
            ax.set_facecolor('#2b2b2b')
            self.figure.patch.set_facecolor('#2b2b2b')
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.title.set_color('white')
        else:
            ax.set_facecolor('white')
            self.figure.patch.set_facecolor('white')
            ax.tick_params(axis='x', colors='black')
            ax.tick_params(axis='y', colors='black')
            ax.xaxis.label.set_color('black')
            ax.yaxis.label.set_color('black')
            ax.title.set_color('black')

        self.canvas.draw()

    def update_graph(self):
        self.plot_graph()

# Classe pour le graphique de progression existant
class ProgressionGraph(QWidget):
    def __init__(self, data, parent_app):
        super().__init__()
        self.original_data = data  # Stocker les données originales sans les modifier
        self.parent_app = parent_app  # Référence à l'application principale pour connaître le mode
        self.show_user = True  # Par défaut, afficher la progression de l'utilisateur

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Ajouter le graphique
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Ajouter une case à cocher pour afficher/masquer la progression de l'utilisateur
        self.checkbox = QCheckBox("Afficher ma progression")
        self.checkbox.setChecked(True)
        self.checkbox.stateChanged.connect(self.update_graph)
        layout.addWidget(self.checkbox)

        self.plot_graph()

    def plot_graph(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Créer des copies locales des données pour éviter de modifier les données originales
        data_copy = [item.copy() for item in self.original_data if item['adversaire'] != username]
        adversaires = [item['adversaire'] for item in data_copy]
        progressions = [item['adversaire_elo_actuel'] - item['adversaire_elo_initial'] for item in data_copy]

        # Trier les données par progression croissante
        data_pairs = list(zip(adversaires, progressions))
        data_pairs.sort(key=lambda x: x[1])  # Tri par progression ascendante
        adversaires_sorted, progressions_sorted = zip(*data_pairs) if data_pairs else ([], [])

        # Convertir en listes pour pouvoir les modifier
        adversaires_sorted = list(adversaires_sorted)
        progressions_sorted = list(progressions_sorted)
        colors = ['blue'] * len(adversaires_sorted)

        # Afficher la progression de l'utilisateur si coché
        if self.checkbox.isChecked():
            # Récupérer les données de l'utilisateur
            user_entry = next((item for item in self.original_data if item['adversaire'] == username), None)
            if user_entry:
                user_progression = user_entry['progression']
                # Trouver la position pour insérer l'utilisateur
                inserted = False
                for i, prog in enumerate(progressions_sorted):
                    if user_progression <= prog:
                        adversaires_sorted.insert(i, username)
                        progressions_sorted.insert(i, user_progression)
                        colors.insert(i, 'gold')
                        inserted = True
                        user_index = i
                        break
                if not inserted:
                    adversaires_sorted.append(username)
                    progressions_sorted.append(user_progression)
                    colors.append('gold')
                    user_index = len(progressions_sorted) - 1
            else:
                # Si l'utilisateur n'a pas de données, on n'affiche rien de plus
                user_index = None
        else:
            user_index = None

        # Créer un histogramme pour les adversaires
        ax.bar(adversaires_sorted, progressions_sorted, color=colors)

        # Ajouter une flèche pour indiquer la position de l'utilisateur
        if user_index is not None:
            ax.annotate(
                'Vous êtes ici',
                xy=(user_index, progressions_sorted[user_index]),
                xytext=(user_index, max(progressions_sorted) * 1.05),
                arrowprops=dict(facecolor='red', shrink=0.05, width=2, headwidth=8),
                ha='center',
                color='red',
                fontsize=12
            )

        # Personnaliser le graphique
        ax.set_xlabel('Joueurs')
        ax.set_ylabel('Progression Elo')
        ax.set_title('Progression des adversaires')
        ax.tick_params(axis='x', rotation=90)
        plt.tight_layout()

        # Ajuster les couleurs pour le mode nuit
        if self.parent_app.is_dark_mode:
            ax.set_facecolor('#2b2b2b')
            self.figure.patch.set_facecolor('#2b2b2b')
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.title.set_color('white')
        else:
            ax.set_facecolor('white')
            self.figure.patch.set_facecolor('white')
            ax.tick_params(axis='x', colors='black')
            ax.tick_params(axis='y', colors='black')
            ax.xaxis.label.set_color('black')
            ax.yaxis.label.set_color('black')
            ax.title.set_color('black')

        self.canvas.draw()

    def update_graph(self):
        self.plot_graph()

# Classe principale de l'application
class ChessApp(QMainWindow):
    def __init__(self, data, adversaries_elo, user_elo_history):
        super().__init__()
        self.setWindowTitle(f"Historique des parties {game_mode.upper()} de {username}")

        # Créer des copies profondes des données pour éviter les modifications non souhaitées
        self.data = [item.copy() for item in data]
        self.adversaries_elo = adversaries_elo.copy()  # Dictionnaire des adversaires uniques et leur Elo actuel
        self.user_elo_history = user_elo_history.copy()  # Liste des tuples (date, elo)
        self.is_dark_mode = False  # Mode jour par défaut

        # Récupérer les données de l'utilisateur et les ajouter à self.data
        self.add_user_entry()

        # Création du widget central et du layout principal
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # Bouton de bascule du mode nuit/jour
        self.toggle_button = QPushButton('🌞')  # Symbole du soleil pour le mode jour
        self.toggle_button.setFixedSize(30, 30)
        self.toggle_button.setStyleSheet('border: none; background-color: transparent; font-size: 20px;')
        self.toggle_button.clicked.connect(self.toggle_dark_mode)
        self.main_layout.addWidget(self.toggle_button, alignment=Qt.AlignRight)

        # Création des onglets
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        # Onglet principal avec la table
        self.table_tab = QWidget()
        self.tabs.addTab(self.table_tab, "Tableau")

        # Onglet pour le graphique de progression
        self.graph_tab = ProgressionGraph(self.data, self)
        self.tabs.addTab(self.graph_tab, "Graphique progression")

        # Onglet pour l'histogramme des Elos actuels
        self.elo_histogram_tab = EloHistogram(self.adversaries_elo, self)
        self.tabs.addTab(self.elo_histogram_tab, "Elo actuel adversaires")

        # Configurer l'onglet de la table
        self.setup_table_tab()

        # Appliquer le style initial
        self.apply_styles()

    def add_user_entry(self):
        # Trouver l'Elo le plus bas et la date correspondante
        if self.user_elo_history:
            self.user_elo_history.sort(key=lambda x: x[1])  # Trier par Elo ascendant
            lowest_elo_date, lowest_elo = self.user_elo_history[0]
        else:
            lowest_elo = None
            lowest_elo_date = None

        # Récupérer l'Elo actuel de l'utilisateur
        user_stats_url = f'https://api.chess.com/pub/player/{username}/stats'
        user_stats_response = requests.get(user_stats_url, headers=headers)
        if user_stats_response.status_code == 200:
            user_stats = user_stats_response.json()
            user_elo_actuel = user_stats.get(rating_type, {}).get('last', {}).get('rating', None)
        else:
            user_elo_actuel = None

        if lowest_elo is not None and user_elo_actuel is not None:
            user_progression = user_elo_actuel - lowest_elo

            # Calcul du score de progression P pour l'utilisateur
            E_initial = lowest_elo
            E_final = user_elo_actuel
            N_parties = len(self.data) if len(self.data) > 0 else 1  # Éviter la division par zéro
            months = 1  # Ajustez si nécessaire

            if E_initial == 0 or E_final == 0:
                P = 0
            else:
                P = (math.log2(E_final / E_initial)) * (12 / months) * (1 + (1 / N_parties))
            P = round(P, 2)

            user_entry = {
                'note_progression': P,
                'date_played': lowest_elo_date,
                'adversaire': username,
                'adversaire_elo_initial': user_elo_actuel,
                'player_elo_initial': lowest_elo,
                'progression': user_progression,
                'adversaire_elo_actuel': user_elo_actuel,
                'color_symbol': '-',  # Non applicable
                'result_symbol': '-'  # Non applicable
            }

            # Ajouter l'entrée de l'utilisateur aux données
            self.data.append(user_entry)

    def toggle_dark_mode(self):
        self.is_dark_mode = not self.is_dark_mode
        if self.is_dark_mode:
            self.toggle_button.setText('🌜')  # Symbole de la lune pour le mode nuit
        else:
            self.toggle_button.setText('🌞')  # Symbole du soleil pour le mode jour
        self.apply_styles()
        self.graph_tab.update_graph()  # Mettre à jour le graphique pour le mode nuit/jour
        self.elo_histogram_tab.update_graph()  # Mettre à jour le nouvel histogramme

    def setup_table_tab(self):
        layout = QVBoxLayout()
        self.table_tab.setLayout(layout)

        # Création du tableau
        self.table = QTableWidget()
        layout.addWidget(self.table)

        # Bouton pour rafraîchir les données
        self.refresh_button = QPushButton("Rafraîchir les données")
        self.refresh_button.clicked.connect(self.refresh_data)
        layout.addWidget(self.refresh_button)

        # Définition des colonnes
        self.columns = [
            ('note_progression', 'Note de progression'),
            ('date_played', 'Date'),
            ('adversaire', 'Adversaire'),
            ('adversaire_elo_initial', 'Elo initial adv.'),
            ('player_elo_initial', 'Mon Elo initial'),
            ('progression', 'Progression'),
            ('adversaire_elo_actuel', 'Elo actuel adv.'),
            ('color_symbol', 'Couleur'),
            ('result_symbol', 'Résultat')
        ]

        self.setup_table()
        self.load_data()
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)

    def setup_table(self):
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels([col[1] for col in self.columns])

    def load_data(self):
        self.table.setRowCount(len(self.data))

        for row_idx, item in enumerate(self.data):
            for col_idx, (key, _) in enumerate(self.columns):
                value = item[key]

                # Formatage spécifique
                if key == 'date_played':
                    cell = DateTableWidgetItem(value)
                elif key in ['progression', 'note_progression', 'adversaire_elo_initial', 'player_elo_initial', 'adversaire_elo_actuel']:
                    cell = NumericTableWidgetItem(value)
                else:
                    display_value = str(value)
                    cell = QTableWidgetItem(display_value)

                # Alignement centré
                cell.setTextAlignment(Qt.AlignCenter)

                # Coloration des cellules
                if key == 'progression':
                    progression_value = value
                    if progression_value > 0:
                        color = QColor('green')
                        display_value = f"+{progression_value}"
                    elif progression_value < 0:
                        color = QColor('red')
                        display_value = f"{progression_value}"
                    else:
                        color = QColor('black')
                        display_value = f"{progression_value}"
                    cell.setForeground(QBrush(color))
                    cell.setText(display_value)

                if key == 'note_progression':
                    P = value
                    if P < 1:
                        color = QColor('#FF8080')  # Rouge clair
                    elif 1 <= P < 2:
                        color = QColor('#FFC080')  # Orange clair
                    elif 2 <= P < 3:
                        color = QColor('#FFFF80')  # Jaune
                    elif 3 <= P < 5:
                        color = QColor('#80FF80')  # Vert clair
                    else:
                        color = QColor('#FF80FF')  # Mauve
                    cell.setForeground(QBrush(color))

                # **Nouvelle section pour colorer le fond de 'result_symbol'**
                if key == 'result_symbol':
                    result_value = value
                    if result_value == 'W':
                        background_color = QColor('green')
                    elif result_value == 'L':
                        background_color = QColor('red')
                    elif result_value == 'D':
                        background_color = QColor('gray')
                    else:
                        background_color = QColor('white')
                    cell.setBackground(QBrush(background_color))
                    # Facultatif : Changer la couleur du texte pour une meilleure lisibilité
                    cell.setForeground(QBrush(QColor('white')))

                # Ajuster les couleurs pour le mode nuit
                if self.is_dark_mode:
                    if key not in ['progression', 'note_progression', 'result_symbol']:
                        cell.setForeground(QBrush(QColor('#dcdcdc')))  # Texte clair sur fond sombre

                self.table.setItem(row_idx, col_idx, cell)

            # Mettre en évidence la ligne de l'utilisateur
            if item['adversaire'].lower() == username.lower():
                for col_idx in range(self.table.columnCount()):
                    self.table.item(row_idx, col_idx).setBackground(QBrush(QColor('gold')))


    def refresh_data(self):
        # Recharger les données
        data, adversaries_elo, user_elo_history = fetch_data()
        self.data = [item.copy() for item in data]
        self.adversaries_elo = adversaries_elo.copy()
        self.user_elo_history = user_elo_history.copy()
        self.add_user_entry()
        self.load_data()
        self.graph_tab.original_data = self.data
        self.graph_tab.update_graph()
        self.elo_histogram_tab.adversaries_elo_original = self.adversaries_elo
        self.elo_histogram_tab.update_graph()

    def apply_styles(self):
        if self.is_dark_mode:
            style = """
            QMainWindow {
                background-color: #2b2b2b;
            }
            QTableWidget {
                background-color: #3c3f41;
                color: #dcdcdc;
                gridline-color: #4d4d4d;
            }
            QHeaderView::section {
                background-color: #3c3f41;
                color: #dcdcdc;
                padding: 4px;
                border: 1px solid #4d4d4d;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                text-align: center;
                font-size: 14px;
                margin: 4px 2px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QTabWidget::pane {
                border-top: 2px solid #C2C7CB;
            }
            QTabBar::tab {
                background: #3c3f41;
                color: #dcdcdc;
                border: 1px solid #4d4d4d;
                padding: 10px;
            }
            QTabBar::tab:selected {
                background: #4d4d4d;
                border-bottom-color: #4d4d4d;
            }
            """
        else:
            style = """
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTableWidget {
                background-color: white;
                color: black;
                gridline-color: #dcdcdc;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                color: black;
                padding: 4px;
                border: 1px solid #dcdcdc;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                text-align: center;
                font-size: 14px;
                margin: 4px 2px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QTabWidget::pane {
                border-top: 2px solid #C2C7CB;
            }
            QTabBar::tab {
                background: #e0e0e0;
                color: black;
                border: 1px solid #C4C4C3;
                padding: 10px;
            }
            QTabBar::tab:selected {
                background: #f0f0f0;
                border-bottom-color: #f0f0f0;
            }
            """
        self.setStyleSheet(style)
        self.load_data()  # Recharger les données pour appliquer les couleurs correctes dans la table

# Fonction principale
def main():
    data, adversaries_elo, user_elo_history = fetch_data()

    app = QApplication(sys.argv)
    window = ChessApp(data, adversaries_elo, user_elo_history)
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
