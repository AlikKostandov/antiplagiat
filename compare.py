import argparse
import ast
import re

def file_parser(input_file):
    with open(input_file, 'r') as file:
        pairs = file.read()
    return pairs


def main():
    parser = argparse.ArgumentParser('File parser')
    parser.add_argument('--infile', help='Input file')
    parser.add_argument('--out', help='Output file')
    args = parser.parse_args()
    if args.infile:
        return file_parser(args.infile)


if __name__ == '__main__':
    pairs = main()

# Получаем пути к паре файлов
docs = pairs.split(' ')


# Получает текст программы из файла по пути
def get_code(path):
    with open(path, 'r') as file:
        code = file.read()
    return code


codes_pair = []


# Очищяем текст от пустых строк и комментариев
def remove_empty_lines_and_comments(text):
    text_lines_list = text.split('\n')
    for line in text_lines_list:
        if len(line) == 0 or line[0] == '#':
            text_lines_list.remove(line)
        if '#' in line:
            text_lines_list[text_lines_list.index(line)] = line[:line.index('#')]
    formatted_text = '\n'.join(text_lines_list)
    return formatted_text


# Применяем это ко всем элементам пары
for doc in docs:
    code = get_code(doc)
    code = remove_empty_lines_and_comments(code)
    codes_pair.append(code)


# Рассчитываем расстояние Левенштейна по алгоритму Вагнера-Фишера
def levenstein(str_1, str_2):
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


# По расстоянию Левенштейна рассчитываем оценку схожести
def calculate_score(levi, length):
    different = length - levi
    answer = different / length
    return round(answer, 2)


# Считаем коэффиецент схожести
def calculate_similarity_score(first_text, second_text):
    text_length = 0
    levenstein_distances_sum = 0

    first_text_lines = first_text.split('\n')
    second_text_lines = second_text.split('\n')

    for i in range(min(len(first_text_lines), len(second_text_lines))):
        text_length = text_length + max(len(first_text_lines[i]), len(second_text_lines[i]))
        levenstein_distances_sum = levenstein_distances_sum + levenstein(first_text_lines[i], second_text_lines[i])

    return calculate_score(levenstein_distances_sum, text_length)


# -------------------------------------------------------------------------
# Получение всех имен переменных
class Visitor(ast.NodeTransformer):
    _constants = []

    def visit_Name(self, node):
        object = node.__getattribute__('id')
        self._constants.append(object)
        self.generic_visit(node)

    def constants(self):
        return self._constants


node = ast.parse(codes_pair[1])
visitor = Visitor()
visitor.visit(node)
variables = set(visitor.constants())


# ------------------------------------------------------------------------------------------
# Создание интервалов функций

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


# Из текста программы возвращает список интервалов функций
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


# Из списка интервалов функций создает деревья из одного элемента
def get_trees_list(intervals_list):
    trees_list = []
    for interval in intervals_list:
        new_tree = Intervaltree(interval, None, None, None)
        trees_list.append(new_tree)
    return trees_list


# Из двух соседних деревьев создает одно
# Если интервал второй функции вложен в интервал первой, то дерево этого интервала становится левым потомком
# Если же этот интервал идет после первого - правым потомком
def update_tree(tree, new_tree):
    if new_tree.interval.begin < tree.interval.end:
        if tree.left is None:
            tree.left = new_tree
            new_tree.parent = tree
        else:
            update_tree(tree.left, new_tree)
    else:
        if tree.right is None:
            tree.right = new_tree
            new_tree.parent = tree
        else:
            update_tree(tree.right, new_tree)
    return tree


# Из списка одноэлементыных деревьев строится одно общее
def build_intervaltree(trees_list):
    tree = trees_list[0]
    trees_list.remove(trees_list[0])
    while len(trees_list) > 0:
        tree = update_tree(tree, trees_list[0])
        trees_list.remove(trees_list[0])
    return tree


# def take_function_priotity(code, node):
#     if node.left is not None:
#         take_function_priotity(code, node.left)
#         ######
#     if node.right is not None:
#         take_function_priotity(code, node.right)


def give_function_part(code, interval):
    begin = interval.begin - 1
    end = interval.end - 1

    lines_number = code.split('\n')

    func = '\n'.join(lines_number[begin:end])
    return func


func_pair = []

for c in codes_pair:
    intervals = parse_file_to_interval_list(c)
    intervals.sort(key=lambda x: x.begin)
    trees_list = get_trees_list(intervals)
    tree = build_intervaltree(trees_list)
    intervals.sort(key=lambda x: x.name)
    func_pair.append(give_function_part(c, intervals[10]))
    for inter in intervals:
        print(inter.name)
    print('##################')


score = calculate_similarity_score(func_pair[0], func_pair[1])
print(score)



