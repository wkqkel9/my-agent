from embed import embed


def cosine_similarity(a, b):
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    size_a = sum(float(x) * float(x) for x in a) ** 0.5
    size_b = sum(float(y) * float(y) for y in b) ** 0.5
    if size_a == 0 or size_b == 0:
        return 0.0
    return dot / (size_a * size_b)


if __name__ == "__main__":
    first = input("첫 번째 문장: ").strip() or "나는 떡볶이를 좋아해"
    second = input("두 번째 문장: ").strip() or "매운 분식을 먹고 싶어"
    score = cosine_similarity(embed(first), embed(second))
    print(f"코사인 유사도: {score:.4f}")
