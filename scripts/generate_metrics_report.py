#!/usr/bin/env python3
"""
Script pour générer des rapports et visualisations des métriques du scraper
"""
import sys
import os
import json
from datetime import datetime
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import argparse

# Ajout du répertoire parent au sys.path pour pouvoir importer config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('metrics-report')

# Fichier des métriques
METRICS_FILE = Path(config.LOG_DIR) / 'scraper_metrics.json'
REPORT_DIR = Path(config.LOG_DIR) / 'reports'
REPORT_DIR.mkdir(exist_ok=True)

def load_metrics():
    """Charge les métriques de scraping du fichier"""
    if not METRICS_FILE.exists():
        logger.error("Fichier de métriques non trouvé")
        return {}
    
    try:
        with open(METRICS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Impossible de charger les métriques: {str(e)}")
        return {}

def generate_success_rate_chart(metrics):
    """Génère un graphique montrant le taux de succès par source"""
    sources = []
    success_rates = []
    
    for source_name, data in metrics.items():
        runs = data.get('runs', 0)
        if runs > 0:
            sources.append(source_name)
            success_rate = data.get('successes', 0) / runs * 100
            success_rates.append(success_rate)
    
    if not sources:
        logger.warning("Pas de données pour générer le graphique de taux de succès")
        return
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(sources, success_rates, color='skyblue')
    
    # Ajouter les valeurs au-dessus des barres
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                 f'{height:.1f}%', ha='center', va='bottom')
    
    plt.title('Taux de succès par source (%)')
    plt.xlabel('Source')
    plt.ylabel('Taux de succès (%)')
    plt.ylim(0, 105)  # Assurer que l'échelle va jusqu'à 100%
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.savefig(REPORT_DIR / 'success_rate.png', dpi=300, bbox_inches='tight')
    plt.close()

def generate_response_time_chart(metrics):
    """Génère un graphique montrant les temps de réponse moyens par source"""
    sources = []
    avg_times = []
    
    for source_name, data in metrics.items():
        response_times = data.get('response_times', [])
        if response_times:
            sources.append(source_name)
            avg_time = sum(response_times) / len(response_times)
            avg_times.append(avg_time)
    
    if not sources:
        logger.warning("Pas de données pour générer le graphique de temps de réponse")
        return
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(sources, avg_times, color='lightgreen')
    
    # Ajouter les valeurs au-dessus des barres
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                 f'{height:.2f}s', ha='center', va='bottom')
    
    plt.title('Temps de réponse moyen par source (secondes)')
    plt.xlabel('Source')
    plt.ylabel('Temps (s)')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.savefig(REPORT_DIR / 'response_time.png', dpi=300, bbox_inches='tight')
    plt.close()

def generate_items_count_chart(metrics):
    """Génère un graphique montrant le nombre moyen d'items par source"""
    sources = []
    avg_counts = []
    
    for source_name, data in metrics.items():
        items_counts = data.get('items_counts', [])
        if items_counts:
            sources.append(source_name)
            avg_count = sum(items_counts) / len(items_counts)
            avg_counts.append(avg_count)
    
    if not sources:
        logger.warning("Pas de données pour générer le graphique de nombre d'items")
        return
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(sources, avg_counts, color='salmon')
    
    # Ajouter les valeurs au-dessus des barres
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                 f'{int(height)}', ha='center', va='bottom')
    
    plt.title('Nombre moyen d\'items par source')
    plt.xlabel('Source')
    plt.ylabel('Nombre d\'items')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.savefig(REPORT_DIR / 'items_count.png', dpi=300, bbox_inches='tight')
    plt.close()

def generate_error_types_chart(metrics):
    """Génère un graphique des types d'erreurs par source"""
    for source_name, data in metrics.items():
        errors = data.get('errors', {})
        if not errors:
            continue
        
        error_types = list(errors.keys())
        error_counts = list(errors.values())
        
        plt.figure(figsize=(10, 6))
        plt.pie(error_counts, labels=error_types, autopct='%1.1f%%', startangle=90)
        plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        plt.title(f'Types d\'erreurs pour {source_name}')
        plt.savefig(REPORT_DIR / f'errors_{source_name}.png', dpi=300, bbox_inches='tight')
        plt.close()

def generate_html_report(metrics):
    """Génère un rapport HTML détaillé des métriques"""
    report_path = REPORT_DIR / 'scraper_report.html'
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Rapport de métriques du scraper - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 10px; }}
            .section {{ margin: 20px 0; padding: 10px; border: 1px solid #ddd; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .chart {{ margin: 20px 0; }}
            .optimal {{ color: green; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Rapport de métriques du scraper</h1>
            <p>Généré le {datetime.now().strftime('%Y-%m-%d à %H:%M')}</p>
        </div>
    """
    
    # Tableau récapitulatif
    html_content += """
        <div class="section">
            <h2>Récapitulatif des sources</h2>
            <table>
                <tr>
                    <th>Source</th>
                    <th>Exécutions</th>
                    <th>Succès</th>
                    <th>Échecs</th>
                    <th>Taux de succès</th>
                    <th>Délai optimal</th>
                    <th>Pages optimales</th>
                    <th>Dernière exécution</th>
                </tr>
    """
    
    for source_name, data in metrics.items():
        runs = data.get('runs', 0)
        successes = data.get('successes', 0)
        failures = data.get('failures', 0)
        success_rate = (successes / runs * 100) if runs > 0 else 0
        optimal_delay = data.get('optimal_delay', config.SCRAPER_DELAY)
        optimal_pages = data.get('optimal_pages', 3)
        last_run = data.get('last_run', 'Jamais')
        
        html_content += f"""
                <tr>
                    <td>{source_name}</td>
                    <td>{runs}</td>
                    <td>{successes}</td>
                    <td>{failures}</td>
                    <td>{success_rate:.1f}%</td>
                    <td class="optimal">{optimal_delay:.2f}s</td>
                    <td class="optimal">{optimal_pages}</td>
                    <td>{last_run}</td>
                </tr>
        """
    
    html_content += """
            </table>
        </div>
    """
    
    # Graphiques
    html_content += """
        <div class="section">
            <h2>Graphiques</h2>
            <div class="chart">
                <h3>Taux de succès par source</h3>
                <img src="success_rate.png" alt="Taux de succès par source" width="800">
            </div>
            <div class="chart">
                <h3>Temps de réponse moyen par source</h3>
                <img src="response_time.png" alt="Temps de réponse moyen par source" width="800">
            </div>
            <div class="chart">
                <h3>Nombre moyen d'items par source</h3>
                <img src="items_count.png" alt="Nombre moyen d'items par source" width="800">
            </div>
    """
    
    # Graphiques d'erreurs pour chaque source
    for source_name in metrics.keys():
        if 'errors' in metrics[source_name] and metrics[source_name]['errors']:
            html_content += f"""
            <div class="chart">
                <h3>Types d'erreurs pour {source_name}</h3>
                <img src="errors_{source_name}.png" alt="Types d'erreurs pour {source_name}" width="800">
            </div>
            """
    
    html_content += """
        </div>
    </body>
    </html>
    """
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Rapport HTML généré: {report_path}")
    return str(report_path)

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description='Générer un rapport de métriques du scraper')
    args = parser.parse_args()
    
    # Charger les métriques
    metrics = load_metrics()
    
    if not metrics:
        logger.error("Aucune métrique disponible")
        return 1
    
    # Générer les graphiques
    generate_success_rate_chart(metrics)
    generate_response_time_chart(metrics)
    generate_items_count_chart(metrics)
    generate_error_types_chart(metrics)
    
    # Générer le rapport HTML
    report_path = generate_html_report(metrics)
    
    logger.info("Génération des rapports terminée")
    print(f"Rapport disponible à l'adresse: file://{report_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
