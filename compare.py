import argparse


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


print(calculate_similarity_score(codes_pair[0], codes_pair[1]))
