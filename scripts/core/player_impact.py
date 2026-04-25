#!/usr/bin/env python3
"""
球员关键度评估模块 v1.0

量化核心球员对球队实力的影响

核心思想：
- 世界杯是赛会制比赛，1-2个核心球员可能改变一切
- 主力前锋缺席 vs 替补前锋缺席，影响天差地别
- 使用转会市场价值作为球员重要性权重

评估维度：
1. 位置重要性：前锋 > 中场 > 守门员 > 后卫
2. 球队依赖度：该球员在队内的不可替代性
3. 当前状态：伤病/停赛/状态起伏
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

BASE_DIR = os.path.expanduser("~/hermes-world-cup/")


# ============ 球员数据 ============

@dataclass
class Player:
    """球员数据"""
    name: str
    position: str  # GK/DEF/MID/FWD
    team: str
    market_value: float  # 百万欧元
    importance: float  # 0-1，该球员在队内的重要程度
    is_key_player: bool  # 是否为核心球员


# ============ 核心球员数据库 ============

TEAM_SQUADS: Dict[str, List[Dict]] = {
    # 顶级强队 - 球员数据
    "Brazil": [
        {"name": "Vinicius Jr", "position": "FWD", "value": 150.0, "importance": 0.95, "key": True},
        {"name": "Neymar", "position": "FWD", "value": 90.0, "importance": 0.90, "key": True},
        {"name": "Rodri", "position": "MID", "value": 120.0, "importance": 0.92, "key": True},
        {"name": "Raphinha", "position": "FWD", "value": 45.0, "importance": 0.75, "key": False},
        {"name": "Alisson", "position": "GK", "value": 45.0, "importance": 0.85, "key": True},
        {"name": "Richarlison", "position": "FWD", "value": 40.0, "importance": 0.70, "key": False},
        {"name": "Casemiro", "position": "MID", "value": 35.0, "importance": 0.80, "key": True},
        {"name": "Marquinhos", "position": "DEF", "value": 35.0, "importance": 0.75, "key": False},
        {"name": "Ederson", "position": "GK", "value": 35.0, "importance": 0.70, "key": False},
        {"name": "Antony", "position": "FWD", "value": 30.0, "importance": 0.65, "key": False},
        {"name": "Raphael Dias", "position": "MID", "value": 55.0, "importance": 0.78, "key": True},
        {"name": "Eder Militao", "position": "DEF", "value": 55.0, "importance": 0.75, "key": False},
    ],
    "France": [
        {"name": "Kylian Mbappe", "position": "FWD", "value": 180.0, "importance": 0.98, "key": True},
        {"name": "Antoine Griezmann", "position": "FWD", "value": 35.0, "importance": 0.85, "key": True},
        {"name": "N'Golo Kante", "position": "MID", "value": 40.0, "importance": 0.88, "key": True},
        {"name": "Aurelien Tchouameni", "position": "MID", "value": 90.0, "importance": 0.82, "key": True},
        {"name": "Eduardo Camavinga", "position": "MID", "value": 70.0, "importance": 0.75, "key": False},
        {"name": "William Saliba", "position": "DEF", "value": 80.0, "importance": 0.82, "key": True},
        {"name": "Theo Hernandez", "position": "DEF", "value": 55.0, "importance": 0.78, "key": True},
        {"name": "Mike Maignan", "position": "GK", "value": 45.0, "importance": 0.80, "key": True},
        {"name": "Ousmane Dembele", "position": "FWD", "value": 55.0, "importance": 0.72, "key": False},
        {"name": "Randal Kolo Muani", "position": "FWD", "value": 65.0, "importance": 0.70, "key": False},
        {"name": "Pau Torres", "position": "DEF", "value": 55.0, "importance": 0.72, "key": False},
        {"name": "Ibrahima Konate", "position": "DEF", "value": 50.0, "importance": 0.70, "key": False},
    ],
    "Argentina": [
        {"name": "Lionel Messi", "position": "FWD", "value": 30.0, "importance": 0.95, "key": True},
        {"name": "Angel Di Maria", "position": "FWD", "value": 25.0, "importance": 0.85, "key": True},
        {"name": "Julián Alvarez", "position": "FWD", "value": 80.0, "importance": 0.88, "key": True},
        {"name": "Enzo Fernandez", "position": "MID", "value": 85.0, "importance": 0.82, "key": True},
        {"name": "Alexis Mac Allister", "position": "MID", "value": 75.0, "importance": 0.80, "key": True},
        {"name": " Cristian Romero", "position": "DEF", "value": 55.0, "importance": 0.78, "key": True},
        {"name": "Emiliano Martinez", "position": "GK", "value": 35.0, "importance": 0.85, "key": True},
        {"name": "Nicolas Otamendi", "position": "DEF", "value": 20.0, "importance": 0.72, "key": False},
        {"name": "Gonzalo Montiel", "position": "DEF", "value": 18.0, "importance": 0.65, "key": False},
        {"name": "Leandro Paredes", "position": "MID", "value": 20.0, "importance": 0.68, "key": False},
        {"name": "Lautaro Martinez", "position": "FWD", "value": 75.0, "importance": 0.82, "key": True},
        {"name": "Exequiel Palacios", "position": "MID", "value": 35.0, "importance": 0.65, "key": False},
    ],
    "Spain": [
        {"name": "Rodri", "position": "MID", "value": 120.0, "importance": 0.95, "key": True},
        {"name": "Pedri", "position": "MID", "value": 100.0, "importance": 0.90, "key": True},
        {"name": "Gavi", "position": "MID", "value": 90.0, "importance": 0.85, "key": True},
        {"name": "Lamine Yamal", "position": "FWD", "value": 130.0, "importance": 0.88, "key": True},
        {"name": "Dani Olmo", "position": "MID", "value": 50.0, "importance": 0.78, "key": True},
        {"name": "Alvaro Morata", "position": "FWD", "value": 25.0, "importance": 0.72, "key": False},
        {"name": "Aymeric Laporte", "position": "DEF", "value": 35.0, "importance": 0.75, "key": False},
        {"name": "David Raya", "position": "GK", "value": 28.0, "importance": 0.70, "key": False},
        {"name": "Nico Williams", "position": "FWD", "value": 60.0, "importance": 0.80, "key": True},
        {"name": "Robin Le Normand", "position": "DEF", "value": 35.0, "importance": 0.72, "key": False},
        {"name": "Mikel Oyarzabal", "position": "FWD", "value": 40.0, "importance": 0.70, "key": False},
        {"name": "Dani Carvajal", "position": "DEF", "value": 35.0, "importance": 0.78, "key": True},
    ],
    "England": [
        {"name": "Jude Bellingham", "position": "MID", "value": 150.0, "importance": 0.95, "key": True},
        {"name": "Harry Kane", "position": "FWD", "value": 110.0, "importance": 0.98, "key": True},
        {"name": "Phil Foden", "position": "MID", "value": 120.0, "importance": 0.90, "key": True},
        {"name": "Bukayo Saka", "position": "FWD", "value": 110.0, "importance": 0.88, "key": True},
        {"name": "Declan Rice", "position": "MID", "value": 100.0, "importance": 0.88, "key": True},
        {"name": "Trent Alexander-Arnold", "position": "DEF", "value": 70.0, "importance": 0.82, "key": True},
        {"name": "Kyle Walker", "position": "DEF", "value": 30.0, "importance": 0.75, "key": False},
        {"name": "Jordan Pickford", "position": "GK", "value": 30.0, "importance": 0.78, "key": True},
        {"name": "John Stones", "position": "DEF", "value": 30.0, "importance": 0.72, "key": False},
        {"name": "Marc Guehi", "position": "DEF", "value": 45.0, "importance": 0.70, "key": False},
        {"name": "Cole Palmer", "position": "MID", "value": 75.0, "importance": 0.80, "key": True},
        {"name": "Jarrod Bowen", "position": "FWD", "value": 45.0, "importance": 0.65, "key": False},
    ],
    "Germany": [
        {"name": "Jamal Musiala", "position": "MID", "value": 130.0, "importance": 0.95, "key": True},
        {"name": "Florian Wirtz", "position": "MID", "value": 120.0, "importance": 0.90, "key": True},
        {"name": "Kai Havertz", "position": "FWD", "value": 70.0, "importance": 0.82, "key": True},
        {"name": "Ilkay Gundogan", "position": "MID", "value": 25.0, "importance": 0.78, "key": False},
        {"name": "Toni Kroos", "position": "MID", "value": 20.0, "importance": 0.85, "key": True},
        {"name": "Manuel Neuer", "position": "GK", "value": 15.0, "importance": 0.88, "key": True},
        {"name": "Antonio Rudiger", "position": "DEF", "value": 30.0, "importance": 0.78, "key": True},
        {"name": "Niklas Sule", "position": "DEF", "value": 28.0, "importance": 0.72, "key": False},
        {"name": "Leroy Sane", "position": "FWD", "value": 55.0, "importance": 0.75, "key": False},
        {"name": "Serge Gnabry", "position": "FWD", "value": 35.0, "importance": 0.70, "key": False},
        {"name": "Jonathan Tah", "position": "DEF", "value": 35.0, "importance": 0.72, "key": False},
        {"name": "Marc-Andre ter Stegen", "position": "GK", "value": 30.0, "importance": 0.75, "key": False},
    ],
    "Portugal": [
        {"name": "Cristiano Ronaldo", "position": "FWD", "value": 15.0, "importance": 0.90, "key": True},
        {"name": "Bruno Fernandes", "position": "MID", "value": 75.0, "importance": 0.92, "key": True},
        {"name": "Bernardo Silva", "position": "MID", "value": 65.0, "importance": 0.88, "key": True},
        {"name": "Ruben Dias", "position": "DEF", "value": 55.0, "importance": 0.85, "key": True},
        {"name": "Joao Felix", "position": "FWD", "value": 45.0, "importance": 0.78, "key": True},
        {"name": "Rafael Leao", "position": "FWD", "value": 55.0, "importance": 0.80, "key": True},
        {"name": "Diogo Jota", "position": "FWD", "value": 45.0, "importance": 0.75, "key": False},
        {"name": "Otavio", "position": "MID", "value": 30.0, "importance": 0.70, "key": False},
        {"name": "Pepe", "position": "DEF", "value": 12.0, "importance": 0.72, "key": False},
        {"name": "Rui Patricio", "position": "GK", "value": 5.0, "importance": 0.65, "key": False},
        {"name": "Nuno Mendes", "position": "DEF", "value": 45.0, "importance": 0.78, "key": True},
        {"name": "Vitinha", "position": "MID", "value": 55.0, "importance": 0.75, "key": False},
    ],
    "Netherlands": [
        {"name": "Virgil van Dijk", "position": "DEF", "value": 30.0, "importance": 0.95, "key": True},
        {"name": "Nathan Ake", "position": "DEF", "value": 45.0, "importance": 0.80, "key": True},
        {"name": "Frenkie de Jong", "position": "MID", "value": 60.0, "importance": 0.90, "key": True},
        {"name": "Teun Koopmeiners", "position": "MID", "value": 50.0, "importance": 0.80, "key": True},
        {"name": "Cody Gakpo", "position": "FWD", "value": 45.0, "importance": 0.85, "key": True},
        {"name": "Xavi Simons", "position": "MID", "value": 55.0, "importance": 0.82, "key": True},
        {"name": "Donyell Malen", "position": "FWD", "value": 35.0, "importance": 0.72, "key": False},
        {"name": "Bart Verbruggen", "position": "GK", "value": 22.0, "importance": 0.72, "key": False},
        {"name": "Daley Blind", "position": "DEF", "value": 12.0, "importance": 0.68, "key": False},
        {"name": "Memphis Depay", "position": "FWD", "value": 20.0, "importance": 0.75, "key": False},
        {"name": "Steven Bergwijn", "position": "FWD", "value": 25.0, "importance": 0.68, "key": False},
        {"name": "Ryan Gravenberch", "position": "MID", "value": 35.0, "importance": 0.70, "key": False},
    ],
    "Italy": [
        {"name": "Gianluigi Donnarumma", "position": "GK", "value": 50.0, "importance": 0.95, "key": True},
        {"name": "Alessandro Bastoni", "position": "DEF", "value": 55.0, "importance": 0.88, "key": True},
        {"name": "Alessio Romagnoli", "position": "DEF", "value": 28.0, "importance": 0.78, "key": False},
        {"name": "Jorginho", "position": "MID", "value": 25.0, "importance": 0.82, "key": True},
        {"name": "Nicolo Barella", "position": "MID", "value": 65.0, "importance": 0.90, "key": True},
        {"name": "Sandro Tonali", "position": "MID", "value": 50.0, "importance": 0.82, "key": True},
        {"name": "Gianluca Scamacca", "position": "FWD", "value": 30.0, "importance": 0.78, "key": True},
        {"name": "Lorenzo Insigne", "position": "FWD", "value": 20.0, "importance": 0.80, "key": True},
        {"name": "Ciro Immobile", "position": "FWD", "value": 25.0, "importance": 0.85, "key": True},
        {"name": "Federico Chiesa", "position": "FWD", "value": 40.0, "importance": 0.88, "key": True},
        {"name": "Leonardo Bonucci", "position": "DEF", "value": 12.0, "importance": 0.72, "key": False},
        {"name": "Gianluca Mancini", "position": "DEF", "value": 22.0, "importance": 0.68, "key": False},
    ],
    "Belgium": [
        {"name": "Kevin De Bruyne", "position": "MID", "value": 45.0, "importance": 0.98, "key": True},
        {"name": "Erling Haaland", "position": "FWD", "value": 180.0, "importance": 0.95, "key": True},
        {"name": "Jeremy Doku", "position": "FWD", "value": 55.0, "importance": 0.78, "key": True},
        {"name": "Leandro Trossard", "position": "FWD", "value": 30.0, "importance": 0.72, "key": False},
        {"name": "Romelu Lukaku", "position": "FWD", "value": 35.0, "importance": 0.85, "key": True},
        {"name": "Youri Tielemans", "position": "MID", "value": 35.0, "importance": 0.78, "key": True},
        {"name": "Koen Casteels", "position": "GK", "value": 18.0, "importance": 0.72, "key": False},
        {"name": "Thibaut Courtois", "position": "GK", "value": 30.0, "importance": 0.90, "key": True},
        {"name": "Jan Vertonghen", "position": "DEF", "value": 8.0, "importance": 0.70, "key": False},
        {"name": "Thomas Meunier", "position": "DEF", "value": 10.0, "importance": 0.65, "key": False},
        {"name": "Charles De Ketelaere", "position": "MID", "value": 30.0, "importance": 0.70, "key": False},
        {"name": "Arthur Theate", "position": "DEF", "value": 22.0, "importance": 0.65, "key": False},
    ],
    "Croatia": [
        {"name": "Luka Modric", "position": "MID", "value": 12.0, "importance": 0.95, "key": True},
        {"name": "Ivan Perisic", "position": "FWD", "value": 15.0, "importance": 0.85, "key": True},
        {"name": "Marcelo Brozovic", "position": "MID", "value": 30.0, "importance": 0.82, "key": True},
        {"name": "Mateo Kovacic", "position": "MID", "value": 35.0, "importance": 0.80, "key": True},
        {"name": "Josko Gvardiol", "position": "DEF", "value": 55.0, "importance": 0.88, "key": True},
        {"name": "Andrej Kramaric", "position": "FWD", "value": 15.0, "importance": 0.78, "key": True},
        {"name": "Mario Pasalic", "position": "MID", "value": 25.0, "importance": 0.72, "key": False},
        {"name": "Dominik Livakovic", "position": "GK", "value": 15.0, "importance": 0.75, "key": False},
        {"name": "Borna Sosa", "position": "DEF", "value": 18.0, "importance": 0.68, "key": False},
        {"name": "Petar Sucic", "position": "MID", "value": 22.0, "importance": 0.65, "key": False},
        {"name": "Luka Ivanusec", "position": "MID", "value": 18.0, "importance": 0.60, "key": False},
        {"name": "Bruno Petkovic", "position": "FWD", "value": 12.0, "importance": 0.62, "key": False},
    ],
    "Uruguay": [
        {"name": "Federico Valverde", "position": "MID", "value": 85.0, "importance": 0.95, "key": True},
        {"name": "Darwin Nunez", "position": "FWD", "value": 65.0, "importance": 0.90, "key": True},
        {"name": "Ronald Araujo", "position": "DEF", "value": 70.0, "importance": 0.88, "key": True},
        {"name": "Rodrigo Bentancur", "position": "MID", "value": 40.0, "importance": 0.80, "key": True},
        {"name": "Mathias Olivera", "position": "DEF", "value": 25.0, "importance": 0.72, "key": False},
        {"name": "Nahitan Nandez", "position": "MID", "value": 22.0, "importance": 0.70, "key": False},
        {"name": "Santiago Mma", "position": "DEF", "value": 20.0, "importance": 0.68, "key": False},
        {"name": "Facundo Pellistri", "position": "FWD", "value": 18.0, "importance": 0.65, "key": False},
        {"name": "Luis Suarez", "position": "FWD", "value": 8.0, "importance": 0.75, "key": False},
        {"name": "Edinson Cavani", "position": "FWD", "value": 6.0, "importance": 0.70, "key": False},
        {"name": "Martin Caceres", "position": "DEF", "value": 5.0, "importance": 0.65, "key": False},
        {"name": "Sebastian Casso", "position": "GK", "value": 8.0, "importance": 0.65, "key": False},
    ],
    "Morocco": [
        {"name": "Achraf Hakimi", "position": "DEF", "value": 55.0, "importance": 0.95, "key": True},
        {"name": "Sofyan Amrabat", "position": "MID", "value": 30.0, "importance": 0.88, "key": True},
        {"name": "Hakim Ziyech", "position": "MID", "value": 25.0, "importance": 0.85, "key": True},
        {"name": "Youssef En-Nesyri", "position": "FWD", "value": 25.0, "importance": 0.82, "key": True},
        {"name": "Ayoub El Kaabi", "position": "FWD", "value": 20.0, "importance": 0.78, "key": True},
        {"name": "Youssef En-Nesyri", "position": "FWD", "value": 20.0, "importance": 0.78, "key": True},
        {"name": "Nayef Aguerd", "position": "DEF", "value": 22.0, "importance": 0.78, "key": True},
        {"name": " Romain Saiss", "position": "DEF", "value": 12.0, "importance": 0.72, "key": False},
        {"name": "Bono", "position": "GK", "value": 15.0, "importance": 0.75, "key": False},
        {"name": "Selim Amalla", "position": "FWD", "value": 18.0, "importance": 0.68, "key": False},
        {"name": "Abdelhamid Sabiri", "position": "MID", "value": 15.0, "importance": 0.65, "key": False},
        {"name": "Jawad El Yamiq", "position": "DEF", "value": 10.0, "importance": 0.60, "key": False},
    ],
    "Colombia": [
        {"name": "Jameiro", "position": "MID", "value": 55.0, "importance": 0.95, "key": True},
        {"name": "Luis Diaz", "position": "FWD", "value": 55.0, "importance": 0.90, "key": True},
        {"name": "Rafael Santos Borre", "position": "FWD", "value": 30.0, "importance": 0.82, "key": True},
        {"name": "Kevin Rodriguez", "position": "FWD", "value": 22.0, "importance": 0.75, "key": False},
        {"name": "Jhon Duran", "position": "FWD", "value": 30.0, "importance": 0.78, "key": True},
        {"name": "Mateo Kolar", "position": "MID", "value": 18.0, "importance": 0.68, "key": False},
        {"name": "David Ospina", "position": "GK", "value": 8.0, "importance": 0.72, "key": False},
        {"name": "Santiago Arias", "position": "DEF", "value": 10.0, "importance": 0.68, "key": False},
        {"name": "Yairo Moreno", "position": "DEF", "value": 12.0, "importance": 0.65, "key": False},
        {"name": "Wilmar Barrios", "position": "MID", "value": 15.0, "importance": 0.72, "key": False},
        {"name": "Jorge Cuadrado", "position": "MID", "value": 10.0, "importance": 0.65, "key": False},
        {"name": "Jhon Lucumi", "position": "DEF", "value": 15.0, "importance": 0.68, "key": False},
    ],
    "USA": [
        {"name": "Christian Pulisic", "position": "MID", "value": 30.0, "importance": 0.95, "key": True},
        {"name": "Sergi Roberto", "position": "DEF", "value": 10.0, "importance": 0.72, "key": False},
        {"name": "Tyler Adams", "position": "MID", "value": 22.0, "importance": 0.88, "key": True},
        {"name": "Giovanni Reyna", "position": "MID", "value": 20.0, "importance": 0.82, "key": True},
        {"name": "Tim Weah", "position": "FWD", "value": 18.0, "importance": 0.78, "key": True},
        {"name": "Christian Pulisic", "position": "FWD", "value": 30.0, "importance": 0.92, "key": True},
        {"name": "Weston McKennie", "position": "MID", "value": 18.0, "importance": 0.80, "key": True},
        {"name": "Matt Turner", "position": "GK", "value": 12.0, "importance": 0.72, "key": False},
        {"name": "Antonee Robinson", "position": "DEF", "value": 15.0, "importance": 0.72, "key": False},
        {"name": "Cameron Carter-Vickers", "position": "DEF", "value": 10.0, "importance": 0.65, "key": False},
        {"name": "Brenden Aaronson", "position": "MID", "value": 18.0, "importance": 0.70, "key": False},
        {"name": "Ricardo Pepi", "position": "FWD", "value": 15.0, "importance": 0.68, "key": False},
    ],
    "Mexico": [
        {"name": "Hirving Lozano", "position": "FWD", "value": 18.0, "importance": 0.92, "key": True},
        {"name": "Edson Alvarez", "position": "MID", "value": 18.0, "importance": 0.88, "key": True},
        {"name": "Alexis Vega", "position": "FWD", "value": 15.0, "importance": 0.82, "key": True},
        {"name": "Jorge Sanchez", "position": "DEF", "value": 10.0, "importance": 0.72, "key": False},
        {"name": "Guillermo Ochoa", "position": "GK", "value": 5.0, "importance": 0.75, "key": False},
        {"name": "Andres Guardado", "position": "MID", "value": 6.0, "importance": 0.72, "key": False},
        {"name": "Uriel Antuna", "position": "FWD", "value": 8.0, "importance": 0.68, "key": False},
        {"name": "Henry Martin", "position": "FWD", "value": 8.0, "importance": 0.65, "key": False},
        {"name": "Cesar Montes", "position": "DEF", "value": 10.0, "importance": 0.68, "key": False},
        {"name": "Juliang Herrera", "position": "MID", "value": 12.0, "importance": 0.70, "key": False},
        {"name": "Luis Chavez", "position": "MID", "value": 10.0, "importance": 0.65, "key": False},
        {"name": "Roberto Alvarado", "position": "FWD", "value": 8.0, "importance": 0.60, "key": False},
    ],
    "Japan": [
        {"name": "Takehiro Minami", "position": "DEF", "value": 18.0, "importance": 0.85, "key": True},
        {"name": "Daizen Maeda", "position": "FWD", "value": 15.0, "importance": 0.80, "key": True},
        {"name": "Kaoru Mitoma", "position": "FWD", "value": 30.0, "importance": 0.90, "key": True},
        {"name": "Jude", "position": "MID", "value": 25.0, "importance": 0.85, "key": True},
        {"name": "Ritsu Doan", "position": "FWD", "value": 22.0, "importance": 0.80, "key": True},
        {"name": "Wataru Endo", "position": "MID", "value": 18.0, "importance": 0.78, "key": False},
        {"name": "Takefusa Kubo", "position": "MID", "value": 25.0, "importance": 0.82, "key": True},
        {"name": "Daichi Kamada", "position": "MID", "value": 18.0, "importance": 0.72, "key": False},
        {"name": "Shui", "position": "GK", "value": 8.0, "importance": 0.68, "key": False},
        {"name": "Maya Yoshida", "position": "DEF", "value": 6.0, "importance": 0.65, "key": False},
        {"name": "Junya Ito", "position": "FWD", "value": 12.0, "importance": 0.65, "key": False},
        {"name": "Hidemasa Morita", "position": "MID", "value": 10.0, "importance": 0.62, "key": False},
    ],
    "Senegal": [
        {"name": "Kalidou Koulibaly", "position": "DEF", "value": 30.0, "importance": 0.95, "key": True},
        {"name": "Sadio Mane", "position": "FWD", "value": 25.0, "importance": 0.92, "key": True},
        {"name": "Boulaye Dia", "position": "FWD", "value": 22.0, "importance": 0.82, "key": True},
        {"name": "Ismaila Sarr", "position": "FWD", "value": 18.0, "importance": 0.78, "key": True},
        {"name": "Nampalys Mendy", "position": "MID", "value": 15.0, "importance": 0.75, "key": False},
        {"name": "Idrissa Gueye", "position": "MID", "value": 12.0, "importance": 0.72, "key": False},
        {"name": "Edouard Mendy", "position": "GK", "value": 12.0, "importance": 0.75, "key": False},
        {"name": "Abdou Diallo", "position": "DEF", "value": 15.0, "importance": 0.68, "key": False},
        {"name": "Krepin Diatta", "position": "MID", "value": 15.0, "importance": 0.68, "key": False},
        {"name": "Moussa Niakhate", "position": "DEF", "value": 12.0, "importance": 0.65, "key": False},
        {"name": "Pape Matar Sarr", "position": "MID", "value": 18.0, "importance": 0.65, "key": False},
        {"name": "Nicolas Jackson", "position": "FWD", "value": 15.0, "importance": 0.60, "key": False},
    ],
}


# ============ 位置权重 ============

POSITION_WEIGHTS = {
    "GK": 0.85,   # 守门员重要，但替补水平差距较小
    "DEF": 0.75,  # 后卫重要
    "MID": 0.90,  # 中场核心，承上启下
    "FWD": 0.95,  # 前锋最关键，得分能力
}


# ============ 球员影响评估器 ============

class PlayerImpactEvaluator:
    """
    球员关键度评估器

    功能：
    1. 计算球队理论最强实力
    2. 评估核心球员缺席的影响
    3. 计算调整后的球队实力
    """

    def __init__(self):
        self.squads = TEAM_SQUADS
        self.position_weights = POSITION_WEIGHTS

    def get_team_squad(self, team: str) -> List[Dict]:
        """获取球队阵容"""
        return self.squads.get(team, [])

    def get_key_players(self, team: str) -> List[Dict]:
        """获取核心球员列表"""
        squad = self.get_team_squad(team)
        return [p for p in squad if p.get("key", False)]

    def calculate_team_strength(self, team: str) -> float:
        """
        计算球队理论最强实力 (0-100)

        基于核心球员的市场价值和位置权重
        """
        squad = self.get_team_squad(team)
        if not squad:
            return 50.0  # 默认中等实力

        # 计算每个球员的贡献值
        player_contributions = []
        for player in squad:
            pos_weight = self.position_weights.get(player["position"], 0.80)
            # 价值归一化（姆巴佩180M作为基准）
            value_factor = min(player["value"] / 180.0, 1.0)
            # 球员贡献 = 位置权重 × 价值因子
            contribution = pos_weight * (0.4 + 0.6 * value_factor)
            player_contributions.append(contribution)

        # 按价值排序
        player_contributions.sort(reverse=True)

        # 前11人贡献 × 10 = 首发阵容实力
        # 乘10是因为贡献值在0-10范围
        starter_strength = sum(player_contributions[:11]) / 11 * 100 if len(player_contributions) >= 11 else sum(player_contributions) / len(player_contributions) * 100 if player_contributions else 50

        return min(starter_strength, 100.0)

    def calculate_player_impact(
        self,
        team: str,
        missing_players: List[str] = None,
        suspended_players: List[str] = None,
    ) -> Dict:
        """
        计算球员缺阵对球队的影响

        Args:
            team: 球队名称
            missing_players: 因伤缺阵的球员列表
            suspended_players: 停赛的球员列表

        Returns:
            影响评估报告
        """
        squad = self.get_team_squad(team)
        if not squad:
            return {
                "team": team,
                "base_strength": 50.0,
                "missing_strength": 0,
                "adjusted_strength": 50.0,
                "impact_percent": 0,
                "missing_players": [],
            }

        # 基础实力
        base_strength = self.calculate_team_strength(team)

        # 计算缺席球员的贡献
        missing = []
        total_impact = 0.0

        all_missing = (missing_players or []) + (suspended_players or [])

        for player_name in all_missing:
            # 找到对应球员
            player_data = None
            for p in squad:
                if p["name"].lower() == player_name.lower():
                    player_data = p
                    break

            if not player_data:
                continue

            # 计算该球员对球队的贡献
            # 算法：姆巴佩180M = 约15%队内贡献（单人损失极限）
            # 普通主力约8-10%，替补更低
            pos_weight = self.position_weights.get(player_data["position"], 0.80)
            value_factor = min(player_data["value"] / 180.0, 1.0)
            importance = player_data.get("importance", 0.7)

            # 缺席影响 = 位置权重 × 价值因子 × 队内重要性 × 15%
            # 15%是单人缺席的最大影响（实际足球中非常罕见）
            impact = pos_weight * value_factor * importance * 15

            total_impact += impact

            missing.append({
                "name": player_data["name"],
                "position": player_data["position"],
                "value": player_data["value"],
                "importance": importance,
                "estimated_impact": round(impact, 2),
            })

        # 调整后的实力
        adjusted_strength = base_strength - total_impact

        # 影响百分比（相对于基础实力的损失）
        impact_percent = (total_impact / base_strength * 100) if base_strength > 0 else 0

        return {
            "team": team,
            "base_strength": round(base_strength, 2),
            "missing_count": len(missing),
            "missing_strength": round(total_impact, 2),
            "adjusted_strength": round(max(adjusted_strength, 0), 2),
            "impact_percent": round(impact_percent, 1),
            "missing_players": missing,
        }

    def compare_teams_with_impact(
        self,
        home_team: str,
        away_team: str,
        home_missing: List[str] = None,
        away_missing: List[str] = None,
    ) -> Dict:
        """
        对比两队实力（考虑球员缺阵）

        Args:
            home_team: 主队
            away_team: 客队
            home_missing: 主队缺阵球员
            away_missing: 客队缺阵球员

        Returns:
            对比报告
        """
        home_impact = self.calculate_player_impact(home_team, missing_players=home_missing)
        away_impact = self.calculate_player_impact(away_team, missing_players=away_missing)

        # 调整后的差距
        strength_diff = home_impact["adjusted_strength"] - away_impact["adjusted_strength"]

        # 胜率调整
        base_home_prob = 0.5 + strength_diff / 200  # 每10分实力差 = 5%胜率

        return {
            "home_team": home_team,
            "away_team": away_team,
            "home": {
                "base_strength": home_impact["base_strength"],
                "adjusted_strength": home_impact["adjusted_strength"],
                "impact_percent": home_impact["impact_percent"],
                "missing_players": home_impact["missing_players"],
            },
            "away": {
                "base_strength": away_impact["base_strength"],
                "adjusted_strength": away_impact["adjusted_strength"],
                "impact_percent": away_impact["impact_percent"],
                "missing_players": away_impact["missing_players"],
            },
            "strength_diff": round(strength_diff, 2),
            "adjusted_home_prob": round(max(0.1, min(0.9, base_home_prob)), 3),
        }

    def get_starter_quality(self, team: str) -> Dict:
        """
        评估球队首发阵容质量

        Returns:
            首发质量评分和深度评分
        """
        squad = self.get_team_squad(team)
        if not squad:
            return {"starter_quality": 50, "bench_quality": 50, "depth_ratio": 1.0}

        # 按价值排序
        sorted_squad = sorted(squad, key=lambda x: x["value"], reverse=True)

        # 首发11人（前11名）
        starters = sorted_squad[:11]
        bench = sorted_squad[11:] if len(sorted_squad) > 11 else []

        # 首发质量
        starter_quality = sum(
            self.position_weights.get(p["position"], 0.80) * min(p["value"] / 180, 1)
            for p in starters
        ) / len(starters) * 100 if starters else 50

        # 替补质量
        bench_quality = sum(
            self.position_weights.get(p["position"], 0.80) * min(p["value"] / 180, 1)
            for p in bench
        ) / len(bench) * 100 if bench else 50

        # 深度比
        depth_ratio = starter_quality / bench_quality if bench_quality > 0 else 1.0

        return {
            "starter_quality": round(starter_quality, 1),
            "bench_quality": round(bench_quality, 1),
            "depth_ratio": round(depth_ratio, 2),
            "key_starter_count": sum(1 for p in starters if p.get("key", False)),
        }


# ============ 测试 ============

if __name__ == "__main__":
    evaluator = PlayerImpactEvaluator()

    print("=" * 60)
    print("⚽ 球员关键度评估测试")
    print("=" * 60)

    # 测试球队实力
    print("\n1. 球队理论最强实力 Top 10:")
    teams = ["Brazil", "France", "Argentina", "Spain", "England",
             "Germany", "Portugal", "Netherlands", "Italy", "Belgium"]
    strengths = [(t, evaluator.calculate_team_strength(t)) for t in teams]
    strengths.sort(key=lambda x: x[1], reverse=True)

    for i, (team, strength) in enumerate(strengths[:10], 1):
        print(f"   {i:>2}. {team:<15} {strength:.1f}")

    # 测试球员缺阵影响
    print("\n2. 球员缺阵影响测试:")
    print("   France 缺少姆巴佩:")
    result = evaluator.calculate_player_impact(
        "France",
        missing_players=["Kylian Mbappe"]
    )
    print(f"   基础实力: {result['base_strength']}")
    print(f"   缺阵影响: -{result['impact_percent']:.1f}%")
    print(f"   调整后: {result['adjusted_strength']}")
    if result["missing_players"]:
        for p in result["missing_players"]:
            print(f"     - {p['name']} ({p['position']}): -{p['estimated_impact']:.1f}")

    # 测试阵容对比
    print("\n3. 阵容对比 (Brazil vs France):")
    comparison = evaluator.compare_teams_with_impact(
        "Brazil", "France",
        home_missing=[],  # Brazil完整阵容
        away_missing=["Kylian Mbappe"]  # France缺姆巴佩
    )
    print(f"   Brazil: {comparison['home']['base_strength']} → {comparison['home']['adjusted_strength']}")
    print(f"   France: {comparison['away']['base_strength']} → {comparison['away']['adjusted_strength']}")
    print(f"   实力差: {comparison['strength_diff']:+.1f}")
    print(f"   调整后胜率: {comparison['adjusted_home_prob']*100:.1f}%")

    # 测试首发质量
    print("\n4. 首发质量 vs 替补深度:")
    for team in ["Brazil", "England", "Germany"]:
        depth = evaluator.get_starter_quality(team)
        print(f"   {team}:")
        print(f"     首发质量: {depth['starter_quality']:.1f}")
        print(f"     替补质量: {depth['bench_quality']:.1f}")
        print(f"     深度比: {depth['depth_ratio']:.2f}")

    print("\n" + "=" * 60)
