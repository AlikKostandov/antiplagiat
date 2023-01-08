import argparse
import ast
import re
import codecs

IMPLEMENTATION_METHOD_WEIGHT = 0.8
SYNTACTIC_DIFFERENCE_WEIGHT = 0.2
COEFFICIENT_SIMILARITY_OF_IMPLEMENTATION_METHOD = 1
COEFFICIENT_SIMILARITY_OF_SYNTACTIC = 1
FILES_NAME_PAIR = []
ARGS = []


# Читает файл input.txt
def file_parser(input_file):
    with open(input_file, 'r') as file:
        pairs = file.read()
    return pairs


def main():
    parser = argparse.ArgumentParser('File parser')
    parser.add_argument('--infile', help='Input file')
    parser.add_argument('--out', help='Output file')
    args = parser.parse_args()
    ARGS.append(args.infile)
    ARGS.append(args.out)
    if args.infile:
        return file_parser(args.infile)


# Запуск
if __name__ == '__main__':
    pairs = main()


# Получает текст программы из файла по пути
def get_code(path):
    with codecs.open(path, 'r', 'utf-8') as file:
        code = file.read()
    return code


# Очищяет текст от пустых строк, комментариев и docstring
def remove_empty_lines_and_comments(text):
    text = re.sub(r'\"{3}[^\)]+\"{3}', '', text)  # Избавляемся от комментариев и docstring  с помощью библиотеки re

    text_lines_list = text.split('\n')
    for line in text_lines_list:
        if len(line) == 0 or line[0] == '#' or line.isspace():
            text_lines_list.remove(line)
        elif '#' in line:
            text_lines_list[text_lines_list.index(line)] = line[:line.index('#')]

    formatted_text = '\n'.join(text_lines_list)
    return formatted_text


# Получает пару текстов
def get_texts_pair():
    PAIRS_LIST = pairs.split('\n')
    for pair in PAIRS_LIST:
        docs = pair.split(' ')
        FILES_NAME_PAIR.append(docs)


# Создание интервалов блоков функций и классов

# Класс интервала
class Interval:
    def __init__(self, name, begin_line_number, end_line_number):
        self.name = name
        self.begin = begin_line_number
        self.end = end_line_number


# Класс дерева интервалов
class Intervaltree:
    def __init__(self, interval, left_child, right_child, parent):
        self.interval = interval
        self.left = left_child
        self.right = right_child
        self.parent = parent


# Из текста программы возвращает список интервалов функций и классов
def parse_file_to_interval_list(program_code: str):
    def node_interval(node: ast.stmt):

        begin = node.lineno
        end = node.lineno

        for node in ast.walk(node):
            if hasattr(node, "lineno"):
                begin = min(begin, node.lineno)
                end = max(end, node.lineno)

        return begin, end + 1

    parsed = ast.parse(program_code)
    interval_list = []

    for item in ast.walk(parsed):
        if isinstance(item, (ast.ClassDef, ast.FunctionDef)):
            interval_ = node_interval(item)
            interval_list.append(Interval(item.name, interval_[0], interval_[1]))

    return interval_list


# Из списка интервалов функций и классов создает деревья из одного элемента
def create_trees_list(intervals_list):
    trees_list = []
    for interval in intervals_list:
        new_tree = Intervaltree(interval, None, None, None)
        trees_list.append(new_tree)

    return trees_list


# Из двух соседних деревьев создает одно общее
# Если интервал второго блока вложен в интервал первого, то дерево этого интервала становится левым потомком
# Если же этот интервал идет после первого - правым потомком
def expand_tree(tree, new_tree):
    if new_tree.interval.begin < tree.interval.end:

        if tree.left is None:
            tree.left = new_tree
            new_tree.parent = tree
        else:
            expand_tree(tree.left, new_tree)

    else:
        if tree.right is None:
            tree.right = new_tree
            new_tree.parent = tree
        else:
            expand_tree(tree.right, new_tree)

    return tree


# Из списка одноэлементыных деревьев строит одно общее
def build_intervaltree(trees_list):
    tree = trees_list[0]
    trees_list.remove(trees_list[0])

    while len(trees_list) > 0:
        tree = expand_tree(tree, trees_list[0])
        trees_list.remove(trees_list[0])

    return tree


# Центрированный обход всего дерева (Левый потомок -> Родитель -> Правый потомок)
def centered_tree_traversal(node, queue):
    if node.left is not None:
        centered_tree_traversal(node.left, queue)

    queue.append(node.interval.name)

    if node.right is not None:
        centered_tree_traversal(node.right, queue)

    return queue


# Заполняет очередь по дереву
def fill_queue_by_tree(intervals):
    trees_list = create_trees_list(intervals)
    tree = build_intervaltree(trees_list)
    queue = []
    return ' -> '.join(centered_tree_traversal(tree, queue))


# Извлекает кусок текста по интервалу
def give_code_part(code, interval):
    begin_line_number = interval.begin - 1
    end_line_number = interval.end - 1

    lines_number = code.split('\n')

    part = '\n'.join(lines_number[begin_line_number:end_line_number])
    return part


# Получает код текста, не входящий ни в один из блоков
def get_non_nested_text(interval, code):
    not_in_block_code = []
    code_list = code.split('\n')

    for line in code_list:
        if line not in interval:
            not_in_block_code.append(line)

    return '\n'.join(not_in_block_code)


# Делит код текста на блоки
def split_program_text(code, intervals):
    blocks_list = []
    copy = code

    for i in range(len(intervals)):
        blocks_list.append(give_code_part(code, intervals[i]))
        copy = get_non_nested_text(give_code_part(code, intervals[i]), copy)

    blocks_list.append(copy)
    return blocks_list


# Рассчитывает расстояние Левенштейна по алгоритму Вагнера-Фишера
def calculate_levenstein_distance(str_1, str_2):
    n, m = len(str_1), len(str_2)

    if n > m:
        str_1, str_2 = str_2, str_1
        n, m = m, n

    current_row = range(n + 1)

    for i in range(1, m + 1):

        previous_row, current_row = current_row, [i] + [0] * n
        for j in range(1, n + 1):

            add, delete, change = previous_row[j] + 1, current_row[j - 1] + 1, previous_row[j - 1]
            if str_1[j - 1] != str_2[i - 1]:
                change += 1
            current_row[j] = min(add, delete, change)

    return current_row[n]


# По расстоянию Левенштейна рассчитывает оценку схожести
def calculate(levi, length):
    different = length - levi
    answer = different / length
    return round(answer, 2)


# Считает коэффиецент схожести
def calculate_similarity_score(first_text, second_text):
    text_length = 0
    levenstein_distances_sum = 0

    first_text_lines = first_text.split('\n')
    second_text_lines = second_text.split('\n')

    for i in range(min(len(first_text_lines), len(second_text_lines))):
        text_length = text_length + max(len(first_text_lines[i]), len(second_text_lines[i]))
        levenstein_distances_sum = levenstein_distances_sum + calculate_levenstein_distance(first_text_lines[i],
                                                                                            second_text_lines[i])

    return calculate(levenstein_distances_sum, text_length)


# -------------------------------------------------------------------------

# Получает все имена переменных
class Visitor(ast.NodeTransformer):
    _constants = []

    def visit_Name(self, node):
        object = node.__getattribute__('id')
        self._constants.append(object)
        self.generic_visit(node)

    def constants(self):
        return self._constants

    # for func in func_pair:
    #     func_node = ast.parse(func)
    #     visitor = Visitor()
    #     visitor.visit(func_node)
    #     func_variables = visitor.constants()
    #     print(list(set(func_variables)))

    # Закончить


# -----------------------------------------------------------------------------------------


# Выдает результат по следующей формуле - синтаксическая разница * вес(СР) + разница реализации * вес(РР)
def get_answer(blocks_list, trees_queue):
    global COEFFICIENT_SIMILARITY_OF_SYNTACTIC, COEFFICIENT_SIMILARITY_OF_IMPLEMENTATION_METHOD
    scores = []

    if len(blocks_list) == 2:
        for i in range(len(blocks_list[0])):
            score = calculate_similarity_score(blocks_list[0][i], blocks_list[1][i])
            scores.append(score)

    if len(scores) > 0:
        COEFFICIENT_SIMILARITY_OF_IMPLEMENTATION_METHOD = round(sum(scores) / len(scores), 2)

    if len(trees_queue) > 0:
        COEFFICIENT_SIMILARITY_OF_SYNTACTIC = calculate_similarity_score(trees_queue[0], trees_queue[1])

    answer = IMPLEMENTATION_METHOD_WEIGHT * COEFFICIENT_SIMILARITY_OF_IMPLEMENTATION_METHOD + COEFFICIENT_SIMILARITY_OF_SYNTACTIC * SYNTACTIC_DIFFERENCE_WEIGHT
    answer = round(answer, 2)
    return answer


# Выявляет показатели метрик и выдает результат
# Синтаксическую разницувыявляет формулой Левенштейна по двум очередям (Т.е. сравнивает два интервальных дерева)
# Разницу реализации считает как среднее между коэффициентами для каждого блока кода
def calculate_similarity_score_for_every_metric():
    answers = []
    get_texts_pair()
    for pair in FILES_NAME_PAIR:
        codes_pair = []
        for el in pair:
            code = get_code(el)
            code = remove_empty_lines_and_comments(code)
            codes_pair.append(code)
        blocks_list = []
        blocks_queue = []

        for code in codes_pair:

            intervals = parse_file_to_interval_list(code)

            intervals.sort(key=lambda x: x.begin)
            if (len(intervals) > 1):
                blocks_queue.append(fill_queue_by_tree(intervals))

            intervals.sort(key=lambda x: x.name)
            blocks_list.append(split_program_text(code, intervals))
        answers.append(get_answer(blocks_list, blocks_queue))
    print(answers)
    return answers

def write_answer_to_file(outfile, answers):
    with open(outfile, 'a') as f:
        for ans in answers:
            f.write(str(ans))
            f.write('\n')

write_answer_to_file(ARGS[1], calculate_similarity_score_for_every_metric())
