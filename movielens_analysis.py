import sys
import time
import requests
from bs4 import BeautifulSoup
import re
import os
from collections import Counter, OrderedDict, defaultdict
from datetime import datetime
import pytest

class Links:

    def __init__(self, path_to_the_file):
        self.file_path = path_to_the_file
        self.links_data = self._load_links_data()

    def _load_links_data(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File '{self.file_path}' does not exist")
        
        links_data = []
        count = 0
        with open(self.file_path, 'r', encoding='utf-8') as f:
            next(f) 
            for line in f:
                if count >= 1000:
                    break
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    links_data.append(parts)
                    count += 1
        return links_data

    def get_imdb_html(self, imdb_id: str):
        
        url = f"https://www.imdb.com/title/tt{imdb_id}/"
        
        headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="131", "Google Chrome";v="131"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }
            
        session = requests.Session()
            
        main_url = "https://www.imdb.com/"
        session.get(main_url, headers=headers)
        time.sleep(1)
            
        response = session.get(url, headers=headers, timeout=15)
            
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")
        
        return response

    def get_imdb(self, html, imdbid):
        soup = BeautifulSoup(html.text, 'html.parser')
        movie_id = imdbid
        
        title = soup.title.string.strip() if soup.title else 'Unknown'
        title = title.replace(' - IMDb', '') 
        
        directors = []
        director_section = soup.find('li', {'data-testid': 'title-pc-principal-credit'})
        if director_section:
            director_links = director_section.find_all('a', href=re.compile(r'/name/nm\d+/'), limit=2)
            directors = [link.get_text(strip=True) for link in director_links if link.get_text(strip=True)]
        directors_str = ' | '.join(directors) if directors else '0'
        
        budget = gross = '0'
        boxoffice_section = soup.find('div', {'data-testid': 'title-boxoffice-section'})
        
        if boxoffice_section:
            budget_li = boxoffice_section.find('li', {'data-testid': 'title-boxoffice-budget'})
            if budget_li:
                budget_span = budget_li.find('span', class_=re.compile(r'ipc-metadata-list-item__list-content-item'))
                if budget_span:
                    budget_text = budget_span.get_text()
                    budget = re.sub(r'[^\d,;]', '', budget_text)
            
            gross_li = boxoffice_section.find('li', {'data-testid': 'title-boxoffice-cumulativeworldwidegross'})
            if gross_li:
                gross_span = gross_li.find('span', class_=re.compile(r'ipc-metadata-list-item__list-content-item'))
                if gross_span:
                    gross_text = gross_span.get_text()
                    gross = re.sub(r'[^\d,;]', '', gross_text) 
        

        runtime_text = '0'
        runtime_section = soup.find('h1', {'data-testid': 'hero__pageTitle'}).find_parent().find('ul') 
        if runtime_section:
            runtime_items = runtime_section.find_all('li')
            for item in runtime_items:
                item_text = item.get_text(strip=True)
                if 'h' in item_text or 'm' in item_text:  
                    runtime_text = item_text
                    break


        runtime = self.parse_runtime(runtime_text)

        imdb_info = [movie_id, directors_str, budget, gross, runtime, title]
        return imdb_info
    
    @staticmethod    
    def parse_runtime(runtime_str):
            if not runtime_str or runtime_str == '0':
                return '0'
            
            hours = 0
            minutes = 0
            
            hours_match = re.search(r'(\d+)h', runtime_str)
            if hours_match: 
                hours = int(hours_match.group(1))
            
            minutes_match = re.search(r'(\d+)m', runtime_str)
            if minutes_match:  
                minutes = int(minutes_match.group(1))
            
            return str(hours * 60 + minutes)

    def save_to_csv(self, data, filename='../datasets/parsed_data.csv'): 
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            
            f.write('movieId,directors,budget,gross,runtime,title\n')
            
            for movie in data:
                
                safe_row = [str(item).replace(',', ';').replace('"', "'") for item in movie]
                f.write(','.join(safe_row) + '\n')

    def write_list_of_imdb_info(self):

        list_of_imdb_info = []
        
        for line in self._load_links_data():
            parts = line.strip().split(',')
            imdbid = parts[1]
            html = self.get_imdb_html(imdbid)
            info_list = self.get_imdb(html, imdbid)
            list_of_imdb_info.append(info_list)
            time.sleep(0.5)
        
        sorted_data = sorted(list_of_imdb_info, key=lambda x: x[0], reverse=True)
        self.save_to_csv(sorted_data)
        return sorted_data
    
    def read_parsed_data(self):

        if not os.path.exists('../datasets/parsed_data.csv'):
            raise FileNotFoundError("../datasets/parsed_data.csv не найден!")
        
        movies = []
        with open('../datasets/parsed_data.csv', 'r', encoding='utf-8') as f:
            next(f)
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 6:
                    movies.append(parts)  
        return movies
    
    def top_directors(self, n):
        """
        :return: словарь топ-n {'Режиссер': количество снятых фильмов}, сортированный по убыванию количества
        """
        movies = self.read_parsed_data()
        directors_count = Counter()
        
        for movie in movies:
            directors = movie[1]  
            if directors != '0':
                directors_count[directors] += 1
        
        directors = dict(sorted(directors_count.items(), 
                                     key=lambda x: x[1], reverse=True)[:n])
        return directors
        
    def most_expensive(self, n):
        """
        :return: топ-n {'Фильм': бюджет фильма}, сортированный по убыванию бюджета
        """
        movies = self.read_parsed_data()
        budget_movies = Counter()
        
        for movie in movies:
            title = movie[5]
            budget_str = movie[2].replace(';', '')
            budget = int(budget_str) if budget_str.isdigit() else 0
            budget_movies[title] = budget
        
        budgets = dict(sorted(budget_movies.items(), 
                                  key=lambda x: x[1], reverse=True)[:n])
        return budgets
        
    def most_profitable(self, n):
        """
        :return: топ-n {'Фильм': разница между кассовыми сборами и бюджетом}, сортированный по убыванию
        """
        movies = self.read_parsed_data()
        profits = {}
        
        for movie in movies:
            title = movie[5]
            budget_str = movie[2].replace(';', '')
            gross_str = movie[3].replace(';', '')
            
            budget = int(budget_str) if budget_str.isdigit() else 0
            gross = int(gross_str) if gross_str.isdigit() else 0
            
            profit = gross - budget
            profits[title] = profit
        
        profits = dict(sorted(profits.items(), 
                                   key=lambda x: x[1], reverse=True)[:n])
        return profits
        
    def longest(self, n):
        """
        :return: топ-n {'Фильм': продолжительность}, сортированный по убыванию продолжительности
        """
        movies = self.read_parsed_data()
        runtimes = {}
        
        for movie in movies:
            title = movie[5]
            runtime = int(movie[4]) if movie[4].isdigit() else 0
            runtimes[title] = runtime
        
        runtimes = dict(sorted(runtimes.items(), 
                                    key=lambda x: x[1], reverse=True)[:n])
        return runtimes
        
    def top_cost_per_minute(self, n):
        """
        :return: топ-n {'Фильм': стоимость экранного времени в минуту}, сортированный по убыванию
        """
        movies = self.read_parsed_data()
        costs = {}
        
        for movie in movies:
            title = movie[5]
            budget_str = movie[2].replace(';', '')

            runtime = int(movie[4]) if movie[4].isdigit() else 1 
            budget = int(budget_str) if budget_str.isdigit() else 0
            if runtime > 0:
                cost_per_min = round(budget / runtime, 2)
                costs[title] = cost_per_min
        
        costs = dict(sorted(costs.items(), 
                                 key=lambda x: x[1], reverse=True)[:n])
        return costs
    
class Movies:

    def __init__(self, path_to_the_file):

        self.file_path = path_to_the_file
        self.movies_data = self._load_movies_data()

    def _parse_csv_line(self, line):
        
        line = line.strip()
        if not line:
            return []
        
        parts = []
        current = ''
        in_quotes = False
        
        i = 0
        while i < len(line):
            char = line[i]
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                parts.append(current.strip())
                current = ''
            else:
                current += char
            i += 1
        parts.append(current.strip())
        return parts

    def _load_movies_data(self):

        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File '{self.file_path}' does not exist")
        
        movies_data = []
        count = 0
        with open(self.file_path, 'r', encoding='utf-8') as f:
            next(f)  
            for line in f:
                if count >= 1000:
                    break
                parts = self._parse_csv_line(line)
                if len(parts) >= 3: 
                    movies_data.append(parts)
                    count += 1
        return movies_data
        


    def dist_by_release(self):
        """
        :return: словарь {'Год': количество фильмов в этом году}, сортированный по убыванию
        """
        release_year = Counter()

        for parts in self.movies_data:
            year_and_movie = parts[1]
            match = re.search(r'\((\d{4})\)', year_and_movie)
            if match:
                    year = match.group(1)
                    release_year[year] += 1
            
        release_years = OrderedDict(sorted(release_year.items(), key=lambda item: item[1], reverse=True))
            

        return release_years
        
       
    def dist_by_genres(self):
        """
        :return: словарь {'Жанр': количество фильмов этого жанра}, сортированный по убыванию
        """
        genres_count = Counter()

        for parts in self.movies_data:
            genres_str = parts[2]
            if genres_str:
                genres = genres_str.split('|')
                for genre in genres:
                    genres_count[genre] += 1
        
        genres = OrderedDict(sorted(genres_count.items(), key=lambda item: item[1], reverse=True))
        
        return genres

        
    def most_genres(self, n):
        
        """
        :return: словарь {'Название': количество жанров}, сортированный по убыванию
        """
        movie_genres_count = Counter()

        for parts in self.movies_data:
            title = parts[1]
            genres_str = parts[2]
            num_genres = len(genres_str.split('|')) if genres_str else 0
            movie_genres_count[title] = num_genres
        
        movies = OrderedDict(sorted(movie_genres_count.items(), key=lambda item: item[1], reverse=True)[:n])
        
        return movies
    
class Ratings:
    
    def __init__(self, ratings_path, movies_path=None, limit=1000):
       
        self.ratings_path = ratings_path
        self.movies_path = movies_path
        self.limit = limit
        self.data = []
        self.movie_titles = {}
        
        self._load_and_merge_data()

    def _load_and_merge_data(self):
        try:
            if self.movies_path and os.path.exists(self.movies_path):
                self._load_movie_titles()

            self._load_ratings_with_titles()
                
        except FileNotFoundError as e:
            print(f"Ошибка: файл не найден - {e}")
            self.data = []
            self.movie_titles = {}
        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
            self.data = []
            self.movie_titles = {}
    
    def _load_movie_titles(self):
        try:
            with open(self.movies_path, 'r', encoding='utf-8') as file:
                next(file)
                for line in file:
                    parts = line.strip().split(',', 2)
                    if len(parts) >= 2:
                        movie_id = int(parts[0])
                        title = parts[1]
                        self.movie_titles[movie_id] = title
        except Exception as e:
            print(f"Ошибка загрузки названий фильмов: {e}")
    
    def _load_ratings_with_titles(self):
        try:
            with open(self.ratings_path, 'r', encoding='utf-8') as file:
                header = file.readline().strip().split(',')
                
                for i, line in enumerate(file):
                    if i >= self.limit:
                        break

                    values = line.strip().split(',')
                    if len(values) == 4:
                        movie_id = int(values[1])
                        
                        record = {
                            'userId': int(values[0]),
                            'movieId': movie_id,
                            'rating': float(values[2]),
                            'timestamp': int(values[3])
                        }
                        
                        if movie_id in self.movie_titles:
                            record['title'] = self.movie_titles[movie_id]
                        else:
                            record['title'] = f"Фильм {movie_id}"
                        
                        self.data.append(record)
                        
        except Exception as e:
            print(f"Ошибка загрузки рейтингов: {e}")
            self.data = []

    def _mean(self, numbers):
        if not numbers:
            return 0
        return sum(numbers) / len(numbers)
    
    def _median(self, numbers):
        if not numbers:
            return 0
        sorted_numbers = sorted(numbers)
        n = len(sorted_numbers)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_numbers[mid - 1] + sorted_numbers[mid]) / 2
        return sorted_numbers[mid]
       
    def _variance(self, numbers):
        if len(numbers) <= 1:
            return 0
        mean_val = self._mean(numbers)
        squared_diff = sum((x - mean_val) ** 2 for x in numbers)
        return squared_diff / len(numbers)
    
    class Movies: 
        def __init__(self, ratings_data):
            self.data = ratings_data
            self.parent = None
            
        def set_parent(self, parent):
            self.parent = parent
            
        def _get_movie_title(self, movie_id):
            for row in self.data:
                if row['movieId'] == movie_id and 'title' in row:
                    return row['title']
            return f"Фильм {movie_id}"
            
        def dist_by_year(self):
            """
            :return: словарь {'Год': количество фильмов}, сортированный по возрастанию года
            """
            ratings_by_year = Counter()
            for row in self.data:
                year = datetime.fromtimestamp(row['timestamp']).year
                ratings_by_year[year] += 1
            
            return dict(sorted(ratings_by_year.items()))
                
        def dist_by_rating(self):
            """
            :return: словарь {'Рейтинг': количество оценок}, сортированный по возрастанию рейтинга
            """
            ratings_distribution = Counter()
            for row in self.data:
                rating = row['rating']
                ratings_distribution[rating] += 1
            
            return dict(sorted(ratings_distribution.items()))
        
        def top_by_num_of_ratings(self, n):
            """
            :return: словарь топ-n {'Название фильма': количество оценок}, сортированный по убыванию количества оценок
            """
            movie_counts = Counter()
            for row in self.data:
                movie_id = row['movieId']
                movie_counts[movie_id] += 1
            
            sorted_counts = sorted(movie_counts.items(), key=lambda x: (-x[1], x[0]))
            
            top_movies = {}
            for movie_id, count in sorted_counts[:n]:
                title = self._get_movie_title(movie_id)
                top_movies[title] = count
        
            return top_movies
        
        def top_by_ratings(self, n, metric='average'):
            """
            :return: словарь топ-n {'Название фильма': средняя/медианная оценка}, сортированный по убыванию оценок
            """ 
            movie_ratings = defaultdict(list)
            for row in self.data:
                movie_ratings[row['movieId']].append(row['rating'])
            
            movie_scores = {}
            for movie_id, ratings in movie_ratings.items():
                if metric == 'average':
                    score = self.parent._mean(ratings)
                elif metric == 'median':
                    score = self.parent._median(ratings)
                else:
                    raise ValueError("Метрика должна быть 'average' или 'median'")
                movie_scores[movie_id] = round(score, 2)
            
            sorted_scores = sorted(movie_scores.items(), key=lambda x: (-x[1], x[0]))
            
            top_movies = {}
            for movie_id, score in sorted_scores[:n]:
                title = self._get_movie_title(movie_id)
                top_movies[title] = score
            
            return top_movies
            
        def top_controversial(self, n, use_sample_variance=False):
            """
            :return: словарь топ-n {'Название фильма': дисперсия}, сортированный по убыванию дисперсии
            """
            movie_ratings = defaultdict(list)
            for row in self.data:
                movie_ratings[row['movieId']].append(row['rating'])
            
            movie_variances = {}
            for movie_id, ratings in movie_ratings.items():
                if len(ratings) >= 2:
                    if use_sample_variance:
                        var = self.parent._variance(ratings)
                    else:
                        mean_val = self.parent._mean(ratings)
                        squared_diff = sum((x - mean_val) ** 2 for x in ratings)
                        var = squared_diff / len(ratings)
                    movie_variances[movie_id] = round(var, 2)
                else:
                    movie_variances[movie_id] = 0.0
            
            sorted_variances = sorted(movie_variances.items(), 
                                    key=lambda x: (-x[1], x[0]))
            
            top_movies = {}
            for movie_id, variance in sorted_variances[:n]:
                title = self._get_movie_title(movie_id)
                top_movies[title] = variance
            
            return top_movies

    class Users(Movies):
        def __init__(self, ratings_data):
            super().__init__(ratings_data)
            
        def dist_by_num_of_ratings(self):
            """
            :return: словарь {'Количество оценок': количество пользователей}, сортированный по возрастанию количества оценок
            """
            user_counts = Counter()
            for row in self.data:
                user_counts[row['userId']] += 1
            
            distribution = Counter()
            for count in user_counts.values():
                distribution[count] += 1
            
            return dict(sorted(distribution.items()))
        
        def dist_by_ratings(self, metric='average'):
            """
            :return: словарь {'Средняя оценка': количество пользователей}, сортированный по возрастанию оценки
            """
            user_ratings = defaultdict(list)
            for row in self.data:
                user_ratings[row['userId']].append(row['rating'])
            
            user_metrics = {}
            for user_id, ratings in user_ratings.items():
                if metric == 'average':
                    score = self.parent._mean(ratings)
                elif metric == 'median':
                    score = self.parent._median(ratings)
                else:
                    raise ValueError("Метрика должна быть 'average' или 'median'")
                user_metrics[user_id] = round(score, 1)
            
            distribution = Counter(user_metrics.values())
            
            return dict(sorted(distribution.items()))
        
        def top_by_variance(self, n):
            """
            :return: словарь топ-n {'Пользователь ID': дисперсия}, сортированный по убыванию дисперсии
            """
            user_ratings = defaultdict(list)
            for row in self.data:
                user_ratings[row['userId']].append(row['rating'])
            
            user_variances = {}
            for user_id, ratings in user_ratings.items():
                var = self.parent._variance(ratings)
                user_variances[user_id] = round(var, 2)
            
            top_items = sorted(user_variances.items(), key=lambda x: (-x[1], x[0]))[:n]
            return dict(top_items)

class Tags:
    
    def __init__(self, path_to_the_file):
        self.path = path_to_the_file
        self.tags = []
        self.load_data()
    
    def load_data(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as file:
                next(file)
                
                for i, line in enumerate(file):
                    if i >= 1000:
                        break
                    
                    parts = line.strip().split(',', 3)
                    if len(parts) >= 3:
                        tag = parts[2].strip()
                        if tag:
                            self.tags.append(tag)

        except FileNotFoundError:
            print(f"Путь к файлу {self.path} не найден")
            self.tags = []
        except Exception as e:
            print("Ошибка загрузка данных")
            self.tags = []

    def most_words(self, n): 
        """
        :return: словарь топ-n {'Теги': количество слов внутри}, сортированный по убыванию количества слов
        """
        unique_tags = {}
        for tag in self.tags:
            if tag not in unique_tags:
                words = re.findall(r'\b\w+\b', tag)
                unique_tags[tag] = len(words)
        
        sorted_tags = sorted(unique_tags.items(), key=lambda x: (-x[1], x[0]))
        
        return dict(sorted_tags[:n])

    def longest(self, n):
        """
        :return: список топ-n (самых длинных тегов), сортированный по убыванию количества символов
        """
        unique_tags = []
        seen = set()
        for tag in self.tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        sorted_tags = sorted(unique_tags, key=lambda x: (-len(x), x))
        
        return sorted_tags[:n]

    def most_words_and_longest(self, n):
        """
        :return: список топ-n (тегов, у которых пересекается наибольшее количество слов и символов), сортированный по убыванию
        """
        most_words_tags = set(self.most_words(n).keys())
        longest_tags = set(self.longest(n))
        intersection = most_words_tags.intersection(longest_tags)
        
        return sorted(intersection)
        
    def most_popular(self, n):
        """
        :return: словарь топ-n самых популярных {'Теги': количество тегов}, сортированный по убыванию количества
        """
        tag_counts = Counter(self.tags)
        top_n = tag_counts.most_common(n)
        
        return dict(top_n)
        
    def tags_with(self, word):
        """
        :return: список уникальных (тегов, у которых есть слово из аргумента), сортированный по алфавиту имен тегов
        """
        word_lower = word.lower()
        matching_tags = set()
        
        for tag in self.tags:
            tag_words = re.findall(r'\b\w+\b', tag.lower())
            if word_lower in tag_words:
                matching_tags.add(tag)
        
        return sorted(matching_tags)



class TestLinks:
    """Тесты для класса Links"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.path_to_link_csv = '../datasets/links.csv'
        if not os.path.exists(self.path_to_link_csv):
            pytest.skip(f"Файл {self.path_to_link_csv} не найден")
        
        if not os.path.exists('../datasets/parsed_data.csv'):
            test_data = """movieId,directors,budget,gross,runtime,title
1,Director A,10000000,50000000,120,Movie A (1995)
2,Director B,20000000,80000000,130,Movie B (1995)
3,Director A,15000000,60000000,110,Movie C (1996)
4,Director C,50000000,200000000,140,Movie D (1996)
5,Director B,30000000,90000000,125,Movie E (1997)
"""
            with open('../datasets/parsed_data.csv', 'w', encoding='utf-8') as f:
                f.write(test_data)
        
        self.links = Links(self.path_to_link_csv)

    def test_top_directors_format(self):
        result = self.links.top_directors(5)
        assert isinstance(result, dict), "Метод должен возвращать словарь"
        
        for key, value in result.items():
            assert isinstance(key, str), f"Ключ '{key}' должен быть строкой"
            assert isinstance(value, int), f"Значение должно быть целым числом"
    
        values = list(result.values())
        assert all(values[i] >= values[i+1] for i in range(len(values)-1)), \
            "Данные должны быть отсортированы по убыванию"
        
    def test_most_expensive_format(self):
        result = self.links.most_expensive(5)
        assert isinstance(result, dict), "Метод должен возвращать словарь"
        
        for key, value in result.items():
            assert isinstance(key, str), f"Ключ '{key}' должен быть строкой"
            assert isinstance(value, int), f"Значение должно быть целым числом"

        values = list(result.values())
        assert all(values[i] >= values[i+1] for i in range(len(values)-1)), \
            "Данные должны быть отсортированы по убыванию"
    
    def test_most_profitable_format(self):
        result = self.links.most_profitable(5)
        assert isinstance(result, dict), "Метод должен возвращать словарь"
        
        for key, value in result.items():
            assert isinstance(key, str), f"Ключ '{key}' должен быть строкой"
            assert isinstance(value, int), f"Значение должно быть целым числом"
        
        values = list(result.values())
        assert all(values[i] >= values[i+1] for i in range(len(values)-1)), \
            "Данные должны быть отсортированы по убыванию"
    
    def test_longest_format(self):
        result = self.links.longest(5)
        assert isinstance(result, dict), "Метод должен возвращать словарь"
        
        for key, value in result.items():
            assert isinstance(key, str), f"Ключ '{key}' должен быть строкой"
            assert isinstance(value, int), f"Значение должно быть целым числом"

        values = list(result.values())
        assert all(values[i] >= values[i+1] for i in range(len(values)-1)), \
            "Данные должны быть отсортированы по убыванию"
    
    def test_top_cost_per_minute_format(self):
        result = self.links.top_cost_per_minute(5)
        assert isinstance(result, dict), "Метод должен возвращать словарь"
        
        for key, value in result.items():
            assert isinstance(key, str), f"Ключ '{key}' должен быть строкой"
            assert isinstance(value, float), f"Значение должно быть float"
        
        values = list(result.values())
        assert all(values[i] >= values[i+1] for i in range(len(values)-1)), \
            "Данные должны быть отсортированы по убыванию"


class TestTags:
    """Тесты для класса Tags"""
    
    @pytest.fixture(autouse=True)
    def setup(self):

        self.path_to_tag_csv = '../datasets/tags.csv'
        if not os.path.exists(self.path_to_tag_csv):
            pytest.skip(f"Файл {self.path_to_tag_csv} не найден")
        self.tags = Tags(self.path_to_tag_csv)
    
    def test_most_words_format(self):
        result = self.tags.most_words(5)
        assert isinstance(result, dict), f"most_words должен возвращать dict, получен {type(result)}"
        
        for key, value in result.items():
            assert isinstance(key, str), f"Ключи должны быть str, получен {type(key)}"
            assert isinstance(value, int), f"Значения должны быть int, получен {type(value)}"
        
        values = list(result.values())
        assert all(values[i] >= values[i+1] for i in range(len(values)-1)), \
            "Данные должны быть отсортированы по убыванию"
    
    def test_longest_format(self):
        result = self.tags.longest(5)
        assert isinstance(result, list), f"longest должен возвращать list, получен {type(result)}"
        
        for item in result:
            assert isinstance(item, str), f"Элементы должны быть str, получен {type(item)}"
        
        # Проверяем правильность сортировки (по убыванию длины)
        lengths = [len(item) for item in result]
        assert all(lengths[i] >= lengths[i+1] for i in range(len(lengths)-1)), \
            "Теги должны быть отсортированы по убыванию длины"
    
    def test_most_words_and_longest_format(self):
        result = self.tags.most_words_and_longest(5)
        assert isinstance(result, list), f"most_words_and_longest должен возвращать list, получен {type(result)}"
        
        for item in result:
            assert isinstance(item, str), f"Элементы должны быть str, получен {type(item)}"
        
        assert result == sorted(result), "Теги должны быть отсортированы по алфавиту"
    
    def test_most_popular_format(self):
        result = self.tags.most_popular(5)
        assert isinstance(result, dict), f"most_popular должен возвращать dict, получен {type(result)}"
        
        for key, value in result.items():
            assert isinstance(key, str), f"Ключи должны быть str, получен {type(key)}"
            assert isinstance(value, int), f"Значения должны быть int, получен {type(value)}"
    
        values = list(result.values())
        assert all(values[i] >= values[i+1] for i in range(len(values)-1)), \
            "Данные должны быть отсортированы по убыванию"
        
    def test_tags_with_format(self):
        result = self.tags.tags_with("comedy")
        assert isinstance(result, list), f"tags_with должен возвращать list, получен {type(result)}"
        
        for item in result:
            assert isinstance(item, str), f"Элементы должны быть str, получен {type(item)}"

        assert result == sorted(result), "Теги должны быть отсортированы по алфавиту"


class TestMovies:
    """Тесты для класса Movies"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
    
        self.path_to_movie_csv = '../datasets/movies.csv'
        if not os.path.exists(self.path_to_movie_csv):
            pytest.skip(f"Файл {self.path_to_movie_csv} не найден")
        self.movies = Movies(self.path_to_movie_csv)
    
    def test_dist_by_release_format_and_sorting(self):
        result = self.movies.dist_by_release()
        
        assert isinstance(result, OrderedDict), "Метод должен возвращать OrderedDict"
        
        for key, value in result.items():
            assert isinstance(key, str), f"Ключ '{key}' должен быть строкой"
            assert isinstance(value, int), f"Значение для ключа '{key}' должно быть целым числом"
            
        values = list(result.values())
        assert all(values[i] >= values[i+1] for i in range(len(values)-1)), \
            "Данные должны быть отсортированы по убыванию"
    
    def test_dist_by_genres_format_and_sorting(self):
        result = self.movies.dist_by_genres()
        
        assert isinstance(result, OrderedDict), "Метод должен возвращать OrderedDict"
        
        for key, value in result.items():
            assert isinstance(key, str), f"Ключ '{key}' должен быть строкой"
            assert isinstance(value, int), f"Значение для ключа '{key}' должно быть целым числом"
            
        values = list(result.values())
        assert all(values[i] >= values[i+1] for i in range(len(values)-1)), \
            "Данные должны быть отсортированы по убыванию"
    
    def test_most_genres_format_and_sorting(self):
        n = 5
        result = self.movies.most_genres(n)
        
        assert isinstance(result, OrderedDict), "Метод должен возвращать OrderedDict"
        
        for key, value in result.items():
            assert isinstance(key, str), f"Ключ '{key}' должен быть строкой"
            assert isinstance(value, int), f"Значение для ключа '{key}' должно быть целым числом"
            
        values = list(result.values())
        assert all(values[i] >= values[i+1] for i in range(len(values)-1)), \
            "Данные должны быть отсортированы по убыванию"


class TestRatings:
    """Тесты для класса Ratings"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
    
        self.path_to_rating_csv = '../datasets/ratings.csv'
        self.path_to_movie_csv = '../datasets/movies.csv'
        if not os.path.exists(self.path_to_rating_csv):
            pytest.skip(f"Файл {self.path_to_rating_csv} не найден")
        self.ratings = Ratings(self.path_to_rating_csv, self.path_to_movie_csv)
    
    def test_dist_by_year(self):
        movies_obj = self.ratings.Movies(self.ratings.data)
        movies_obj.set_parent(self.ratings)
        result = movies_obj.dist_by_year()
        
        assert isinstance(result, dict), "Метод должен возвращать словарь"
        
        for key, value in result.items():
            assert isinstance(key, int), f"Ключ '{key}' должен быть целым числом"
            assert isinstance(value, int), f"Значение должно быть целым числом"
        
        keys = list(result.keys())
        assert all(keys[i] <= keys[i+1] for i in range(len(keys)-1)), \
            "Года должны быть отсортированы по возрастанию"
    
    def test_dist_by_rating(self):
        movies_obj = self.ratings.Movies(self.ratings.data)
        movies_obj.set_parent(self.ratings)
        result = movies_obj.dist_by_rating()
        
        assert isinstance(result, dict), "Метод должен возвращать словарь"
        
        for key, value in result.items():
            assert isinstance(key, float), f"Ключ '{key}' должен быть float"
            assert isinstance(value, int), f"Значение должно быть целым числом"
        
        keys = list(result.keys())
        assert all(keys[i] <= keys[i+1] for i in range(len(keys)-1)), \
            "Рейтинги должны быть отсортированы по возрастанию"
    
    def test_top_by_num_of_ratings(self):
        movies_obj = self.ratings.Movies(self.ratings.data)
        movies_obj.set_parent(self.ratings)
        n = 5
        result = movies_obj.top_by_num_of_ratings(n)
        
        assert isinstance(result, dict), "Метод должен возвращать словарь"
        
        for key, value in result.items():
            assert isinstance(key, str), f"Ключ '{key}' должен быть строкой"
            assert isinstance(value, int), f"Значение должно быть целым числом"
        
        values = list(result.values())
        assert all(values[i] >= values[i+1] for i in range(len(values)-1)), \
            "Данные должны быть отсортированы по убыванию"
    
    def test_top_by_ratings(self):
        movies_obj = self.ratings.Movies(self.ratings.data)
        movies_obj.set_parent(self.ratings)
        n = 5
        result = movies_obj.top_by_ratings(n, 'average')
        
        assert isinstance(result, dict), "Метод должен возвращать словарь"
        
        for key, value in result.items():
            assert isinstance(key, str), f"Ключ '{key}' должен быть строкой"
            assert isinstance(value, float), f"Значение должно быть float"
        
        values = list(result.values())
        assert all(values[i] >= values[i+1] for i in range(len(values)-1)), \
            "Данные должны быть отсортированы по убыванию"
    
    def test_top_controversial(self):
        movies_obj = self.ratings.Movies(self.ratings.data)
        movies_obj.set_parent(self.ratings)
        n = 5
        result = movies_obj.top_controversial(n)
        
        assert isinstance(result, dict), "Метод должен возвращать словарь"
        
        for key, value in result.items():
            assert isinstance(key, str), f"Ключ '{key}' должен быть строкой"
            assert isinstance(value, float), f"Значение должно быть float"
        
        values = list(result.values())
        assert all(values[i] >= values[i+1] for i in range(len(values)-1)), \
            "Данные должны быть отсортированы по убыванию"
    
    def test_dist_by_num_of_ratings_users(self):
        users_obj = self.ratings.Users(self.ratings.data)
        users_obj.set_parent(self.ratings)
        result = users_obj.dist_by_num_of_ratings()
        
        assert isinstance(result, dict), "Метод должен возвращать словарь"
        
        for key, value in result.items():
            assert isinstance(key, int), f"Ключ '{key}' должен быть целым числом"
            assert isinstance(value, int), f"Значение должно быть целым числом"
        
        keys = list(result.keys())
        assert all(keys[i] <= keys[i+1] for i in range(len(keys)-1)), \
            "Количества оценок должны быть отсортированы по возрастанию"
    
    def test_dist_by_ratings_users(self):
        users_obj = self.ratings.Users(self.ratings.data)
        users_obj.set_parent(self.ratings)
        result = users_obj.dist_by_ratings('average')
        
        assert isinstance(result, dict), "Метод должен возвращать словарь"
        
        for key, value in result.items():
            assert isinstance(key, float), f"Ключ '{key}' должен быть float"
            assert isinstance(value, int), f"Значение должно быть целым числом"
    
        keys = list(result.keys())
        assert all(keys[i] <= keys[i+1] for i in range(len(keys)-1)), \
            "Рейтинги должны быть отсортированы по возрастанию"
        
    def test_top_by_variance_users(self):
        users_obj = self.ratings.Users(self.ratings.data)
        users_obj.set_parent(self.ratings)
        n = 5
        result = users_obj.top_by_variance(n)
        
        assert isinstance(result, dict), "Метод должен возвращать словарь"
        
        for key, value in result.items():
            assert isinstance(key, int), f"Ключ '{key}' должен быть целым числом"
            assert isinstance(value, float), f"Значение должно быть float"
        
        values = list(result.values())
        assert all(values[i] >= values[i+1] for i in range(len(values)-1)), \
            "Данные должны быть отсортированы по убыванию"

if __name__ == "__main__":

    links = Links('../datasets/links.csv')
    print("Top 10 directors:", links.top_directors(10))
    print("Top 10 expensive:", links.most_expensive(10))
    print("Top 10 profitable:", links.most_profitable(10))
    print("Top 10 longest:", links.longest(10))
    print("Top 10 cost/min:", links.top_cost_per_minute(10))

    movies = Movies('../datasets//movies.csv')
    print("Dist by release:", movies.dist_by_release())
    print("Dist by genres:", movies.dist_by_genres())
    print("Top 10 most genres:", movies.most_genres(10))

    ratings = Ratings('../datasets/ratings.csv', '../datasets/movies.csv')
    movies = ratings.Movies(ratings.data)
    movies.set_parent(ratings)
    print("Movies dist by year:", movies.dist_by_year())
    print("Dist by rating:", movies.dist_by_rating())
    print("Top 10 by num ratings:", movies.top_by_num_of_ratings(10))
    print("Top 10 avg ratings:", movies.top_by_ratings(10, 'average'))
    print("Top 10 controversial:", movies.top_controversial(10))
    
    users = ratings.Users(ratings.data)
    users.set_parent(ratings)
    print("Users dist num ratings:", users.dist_by_num_of_ratings())
    print("Users dist avg ratings:", users.dist_by_ratings('average'))
    print("Top 10 user variance:", users.top_by_variance(10))

    tags = Tags('../datasets/tags.csv')
    print("Most words tags:", tags.most_words(10))
    print("Longest tags:", tags.longest(10))
    print("Most words & longest:", tags.most_words_and_longest(10))
    print("Most popular:", tags.most_popular(10))
    print("Tags with 'action':", tags.tags_with('action'))
 