import tempfile
from pathlib import Path

from copydetect import CopyDetector

from ...models.plagiarism import CodeSubmission, PlagiarismMatch
from ...services.plagiarism.base import BasePlagiarismStrategy
from ...utils.preprocessing import CppPreprocessor, JavaPreprocessor, PythonPreprocessor


class CopydetectStrategy(BasePlagiarismStrategy):

    def __init__(
        self,
        language: str = "python",
        noise_threshold: int = 25,
        guarantee_threshold: int = 25,
    ):
        self.language = language
        self.noise_threshold = noise_threshold
        self.guarantee_threshold = guarantee_threshold
        if language == "python":
            self.preprocessor = PythonPreprocessor()
        elif language == "cpp":
            self.preprocessor = CppPreprocessor()
        elif language == "java":
            self.preprocessor = JavaPreprocessor()
        else:
            self.preprocessor = None

    async def check(self, submissions: list[CodeSubmission]) -> list[PlagiarismMatch]:
        matches = []

        # copydetect работает с файлами, поэтому создаем временную директорию
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            path_to_id = {}

            # Сохраняем все посылки во временные файлы
            for sub in submissions:
                code = (
                    self.preprocessor.preprocess(sub.code)
                    if self.preprocessor
                    else sub.code
                )
                file_path = temp_path / f"sub_{sub.id}.txt"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(code)

                path_to_id[str(file_path.absolute())] = sub.id

            detector = CopyDetector(
                noise_t=self.noise_threshold,
                guarantee_t=self.guarantee_threshold,
                display_t=0.0,  # Нам нужны все результаты, даже с 0% сходства
                force_language=self.language,
                silent=True,  # Отключаем логирование в консоль
                disable_filtering=False,
            )

            for file_path in path_to_id.keys():
                detector.add_file(file_path, type="testref")

            detector.run()

            results = detector.get_copied_code_list()

            # массив массивов: [test_similarity, reference_similarity, test_file_path, ref_file_path, ...]
            from itertools import combinations

            pair_scores = {}
            for sub_a, sub_b in combinations(submissions, 2):
                pair_key = tuple(sorted([str(sub_a.id), str(sub_b.id)]))
                pair_scores[pair_key] = {
                    "source_id": sub_a.id,
                    "target_id": sub_b.id,
                    "score": 0.0,
                }

            for item in results:
                sim_test = item[0]  # сходство файла 1 с файлом 2
                sim_ref = item[1]  # сходство файла 2 с файлом 1
                path_a = item[2]
                path_b = item[3]

                id_a = path_to_id.get(path_a)
                id_b = path_to_id.get(path_b)

                # игнорируем сравнение файла с самим собой
                if id_a is None or id_b is None or id_a == id_b:
                    continue

                # norm
                pair_key = tuple(sorted([str(id_a), str(id_b)]))

                if pair_key in pair_scores:
                    # берем максимальное сходство из двух
                    score = (
                        float(max(sim_test, sim_ref) * 100)
                        if isinstance(sim_test, float)
                        else float(max(sim_test, sim_ref) * 100)
                    )
                    pair_scores[pair_key]["score"] = max(
                        pair_scores[pair_key]["score"], score
                    )

            for pair_data in pair_scores.values():
                matches.append(
                    PlagiarismMatch(
                        source_id=pair_data["source_id"],
                        target_id=pair_data["target_id"],
                        score=pair_data["score"],
                        details={"method": "copydetect_winnowing"},
                    )
                )

        return matches
