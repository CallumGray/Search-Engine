import json
import string
import numpy
import time
from collections import Counter

build_time = time.time()
print()
print('Building...')

with open('recipes.json') as file:
    data = json.load(file)

for recipe in data:
    if 'categories' not in recipe:
        recipe['categories'] = []
    if 'ingredients' not in recipe:
        recipe['ingredients'] = []
    if 'directions' not in recipe:
        recipe['directions'] = []
    if 'calories' not in recipe:
        recipe['calories'] = -1
    if 'fat' not in recipe:
        recipe['fat'] = -1
    if 'protein' not in recipe:
        recipe['protein'] = -1
    if 'rating' not in recipe:
        recipe['rating'] = 0

dataID = {i:recipe for i, recipe in enumerate(data)}

# Gives set (no duplicates) or list (duplicates) of tokens from string
def tokenise(input_string, return_set=True):
    # Convert punctuation and digits to spaces (use string.punctuation / string.digits)
    punctuation = str.maketrans(string.punctuation, ' ' * len(string.punctuation))
    digits = str.maketrans(string.digits, ' ' * len(string.digits))

    input_string = input_string.translate(punctuation)
    input_string = input_string.translate(digits)

    # Use split() to extract data
    tokens = str.split(input_string)

    if return_set:
        # Ignore all tokens less than 3 characters and make all lowercase
        tokens = set(str.lower(token) for token in tokens if len(token) > 2)
    else:
        tokens = [str.lower(token) for token in tokens if len(token) > 2]

    # Return list of tokens
    return tokens


def stringlist2string(input_list):
    string_out = ''
    for s in input_list:
        string_out += s + ' '
    return string_out


# Takes the recipe dictionary and gets a set of all words within, with scores for each word...
def get_recipe_words(recipe):

    title = tokenise(recipe['title'],False)
    categories = tokenise(stringlist2string(recipe['categories']),False)
    ingredients = tokenise(stringlist2string(recipe['ingredients']),False)
    directions = tokenise(stringlist2string(recipe['directions']),False)

    title_count = Counter(title)
    categories_count = Counter(categories)
    ingredients_count = Counter(ingredients)
    directions_count = Counter(directions)

    # Dictionary of word:score
    union = set.union(set(title), categories, ingredients, directions)
    word_score = {}

    for word in union:
        score = 0
        score += 8 * title_count[word]
        score += 4 * categories_count[word]
        score += 2 * ingredients_count[word]
        score += directions_count[word]
        word_score[word] = score

    return word_score


#
#
#   SCORING FUNCTIONS
#
#


def simple_score(recipe):
    directions = len(recipe['directions'])
    ingredients = len(recipe['ingredients'])

    if directions < 2 or ingredients < 2:
        return -1

    return ingredients * directions


def simple_score_all(recipes):

    scored_recipes = [(simple_score(recipe), recipe) for recipe in recipes if simple_score(recipe) > 0]
    return scored_recipes


def healthy_score(recipe):
    calories = recipe['calories']
    fat = recipe['fat']
    protein = recipe['protein']

    if calories < 0 or fat < 0 or protein < 0:
        return -1

    max_n = 1

    while calories - 510 * max_n > 0:
        max_n += 1

    while fat - 150 * max_n > 0:
        max_n += 1

    while protein - 18 * max_n > 0:
        max_n += 1

    best_score = numpy.inf

    for n in range(1, max_n + 1):
        calories_calc = numpy.fabs(calories - 510 * n) / 510
        fat_calc = numpy.fabs(fat - 150 * n) / 150
        protein_calc = numpy.fabs(protein - 18 * n) / 18
        best_score = min(calories_calc + 4 * fat_calc + 2 * protein_calc, best_score)

    return best_score


def healthy_score_all(recipes):
    scored_recipes = [(healthy_score(recipe), recipe) for recipe in recipes if healthy_score(recipe) >= 0]
    return scored_recipes


# GIVEN AS A TUPLE (score,recipe)
def sort_recipes(recipes, descending=True):
    recipes.sort(key=lambda x: x[0], reverse=descending)
    return recipes


#
#
#  INVERTED INDEX AND SEARCH
#
#

# inverse_index[word] = {id:{recipe},id4:{recipe4} ... }

inverse_index = {}

for ID, recipe in dataID.items():
    for word,score in get_recipe_words(recipe).items():
        if word in inverse_index:
            inverse_index[word][ID] = (score,recipe)
        else:
            inverse_index[word] = {ID: (score,recipe)}

def do_search(query, ordering='normal', count=10):
    search_time = time.time()

    querywords = tokenise(query)
    query_sets = []

    for queryword in querywords:
        if queryword in inverse_index:
            # Get set of ids for each word
            query_set = set(inverse_index[queryword].keys())
            query_sets.append(query_set)
        else:
            # So an intersection of len 1 with an unmatched word doesn't throw an error
            query_sets.append(set())

    matching_recipes = []

    # Need at least 1 set to use intersection
    if len(query_sets) > 0:
        # IDs with all query words
        final_ids = set.intersection(*query_sets)

        if ordering == 'normal':
            for ID in final_ids:

                final_score = 0
                final_recipe = None

                for queryword in querywords:

                    (score_one_word,new_recipe) = inverse_index[queryword][ID]
                    final_score += score_one_word
                    final_recipe = new_recipe

                final_score += final_recipe['rating']
                matching_recipes.append((final_score,final_recipe))
        elif ordering == 'healthy' or ordering == 'simple':
            matching_recipes = [dataID[matching_id] for matching_id in final_ids]
        else:
            print('Invalid ordering')
            return None
    else:
        matching_recipes = []

    if ordering == 'normal':
        sorted_recipes = sort_recipes(matching_recipes)
    elif ordering == 'healthy':
        scored_recipes = healthy_score_all(matching_recipes)
        sorted_recipes = sort_recipes(scored_recipes, False)
    elif ordering == 'simple':
        scored_recipes = simple_score_all(matching_recipes)
        sorted_recipes = sort_recipes(scored_recipes, False)
    else:
        print('Invalid ordering')
        return None

    for i in range(min(count, len(sorted_recipes))):
        print(sorted_recipes[i][1]['title'])

    search_time = time.time() - search_time
    print()
    print('Search Time: ', search_time)
    print()
    print()

build_time = time.time() - build_time
print("Build Time: ",build_time)

while (True):
    order_input = ''
    while str.lower(order_input) != 'h' and str.lower(order_input) != 's' and str.lower(order_input) != 'n':
        order_input = input("Ordering? [N] - Normal, [S] - Simple, [H] - Healthy\n")

    if order_input == 'h':
        order_input = 'healthy'
    elif order_input == 'n':
        order_input = 'normal'
    else:
        order_input = 'simple'

    count_input = None

    while type(count_input) != int:
        # Count
        try:
            count_input = int(input("Max amount of searches?\n"))
        except ValueError:
            print("Not a valid integer\n")

    while True:
        # Takes string search
        search_input = input("SEARCH TERM\n")
        # Searches!
        print()
        do_search(search_input, order_input, count_input)