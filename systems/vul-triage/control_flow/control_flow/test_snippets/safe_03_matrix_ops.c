/*
 * safe_03_matrix_ops.c
 * 安全的矩阵加法与转置 —— 无漏洞
 * 所有索引运算均在已知维度范围内进行。
 */
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    int rows;
    int cols;
    int *data;
} Matrix;

Matrix *matrix_create(int rows, int cols) {
    if (rows <= 0 || cols <= 0) return NULL;
    Matrix *m = (Matrix *)malloc(sizeof(Matrix));
    if (!m) return NULL;
    m->rows = rows;
    m->cols = cols;
    m->data = (int *)calloc((size_t)rows * cols, sizeof(int));
    if (!m->data) { free(m); return NULL; }
    return m;
}

void matrix_free(Matrix *m) {
    if (m) {
        free(m->data);
        free(m);
    }
}

int matrix_get(const Matrix *m, int r, int c) {
    if (!m || r < 0 || r >= m->rows || c < 0 || c >= m->cols) return 0;
    return m->data[r * m->cols + c];
}

void matrix_set(Matrix *m, int r, int c, int val) {
    if (!m || r < 0 || r >= m->rows || c < 0 || c >= m->cols) return;
    m->data[r * m->cols + c] = val;
}

Matrix *matrix_add(const Matrix *a, const Matrix *b) {
    if (!a || !b || a->rows != b->rows || a->cols != b->cols) return NULL;
    Matrix *c = matrix_create(a->rows, a->cols);
    if (!c) return NULL;
    for (int i = 0; i < a->rows; i++) {
        for (int j = 0; j < a->cols; j++) {
            matrix_set(c, i, j, matrix_get(a, i, j) + matrix_get(b, i, j));
        }
    }
    return c;
}

Matrix *matrix_transpose(const Matrix *m) {
    if (!m) return NULL;
    Matrix *t = matrix_create(m->cols, m->rows);
    if (!t) return NULL;
    for (int i = 0; i < m->rows; i++) {
        for (int j = 0; j < m->cols; j++) {
            matrix_set(t, j, i, matrix_get(m, i, j));
        }
    }
    return t;
}

void matrix_print(const Matrix *m) {
    if (!m) return;
    for (int i = 0; i < m->rows; i++) {
        for (int j = 0; j < m->cols; j++) {
            printf("%4d ", matrix_get(m, i, j));
        }
        printf("\n");
    }
}

int main(void) {
    Matrix *a = matrix_create(3, 3);
    Matrix *b = matrix_create(3, 3);
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 3; j++) {
            matrix_set(a, i, j, i + j);
            matrix_set(b, i, j, (i + 1) * (j + 1));
        }

    Matrix *c = matrix_add(a, b);
    Matrix *t = matrix_transpose(a);

    printf("A + B:\n"); matrix_print(c);
    printf("Transpose A:\n"); matrix_print(t);

    matrix_free(a); matrix_free(b);
    matrix_free(c); matrix_free(t);
    return 0;
}
