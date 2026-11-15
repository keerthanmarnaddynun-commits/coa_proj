import os

path = r'c:\Users\Kirthan\Desktop\os proj\pp\graph.c'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_trace_log = """static inline void trace_log(TraceLogger *logger, char *buf, size_t *len, uint64_t *count,
                             const char *op, const void *addr, const char *array, uint64_t idx) {
    if (!logger || !logger->enabled) return;
    if (*len > TRACE_BUF_SIZE - 256) {
        trace_flush(logger, buf, len, count);
    }
    int written = snprintf(buf + *len, TRACE_BUF_SIZE - *len, "%s %p %s[%llu]\\n",
                           op, addr, array, (unsigned long long)idx);
    if (written > 0) {
        *len += (size_t)written;
        (*count)++;
    }
}"""

new_trace_log = """static inline void trace_log(TraceLogger *logger, char *buf, size_t *len, uint64_t *count,
                             int tid, const char *op, const void *addr, const char *array, uint64_t idx) {
    if (!logger || !logger->enabled) return;
    if (*len > TRACE_BUF_SIZE - 256) {
        trace_flush(logger, buf, len, count);
    }
    int written = snprintf(buf + *len, TRACE_BUF_SIZE - *len, "T%d %s %p %s[%llu]\\n",
                           tid, op, addr, array, (unsigned long long)idx);
    if (written > 0) {
        *len += (size_t)written;
        (*count)++;
    }
}"""

old_root = """            /* Log root initialization */
            fprintf(logger.fp, "WRITE %p distances[%u]\\n", (void *)&distances[root], root);
            fprintf(logger.fp, "WRITE %p frontier[0]\\n", (void *)&frontier[0]);"""

new_root = """            /* Log root initialization */
            fprintf(logger.fp, "T0 WRITE %p distances[%u]\\n", (void *)&distances[root], root);
            fprintf(logger.fp, "T0 WRITE %p frontier[0]\\n", (void *)&frontier[0]);"""

old_task = """                        #pragma omp task firstprivate(start, end)
                        {
                            char local_buf[TRACE_BUF_SIZE];
                            size_t local_len = 0;
                            uint64_t local_count = 0;

                            for (size_t idx = start; idx < end; idx++) {
                                trace_log(&logger, local_buf, &local_len, &local_count,
                                          "READ", &frontier[idx], "frontier", idx);
                                node_t u = frontier[idx];

                                trace_log(&logger, local_buf, &local_len, &local_count,
                                          "READ", &graph->row_pointers[u], "row_pointers", u);
                                edge_t start_edge = graph->row_pointers[u];

                                trace_log(&logger, local_buf, &local_len, &local_count,
                                          "READ", &graph->row_pointers[u + 1], "row_pointers", u + 1);
                                edge_t end_edge = graph->row_pointers[u + 1];

                                for (edge_t e = start_edge; e < end_edge; e++) {
                                    trace_log(&logger, local_buf, &local_len, &local_count,
                                              "READ", &graph->column_indices[e], "column_indices", e);
                                    node_t v = graph->column_indices[e];

                                    trace_log(&logger, local_buf, &local_len, &local_count,
                                              "READ", &distances[v], "distances", v);
                                    if (distances[v] == -1) {
                                        if (__sync_bool_compare_and_swap(&distances[v], -1, current_level + 1)) {
                                            trace_log(&logger, local_buf, &local_len, &local_count,
                                                      "WRITE", &distances[v], "distances", v);
                                            size_t pos = __sync_fetch_and_add(&next_size, 1);
                                            next_frontier[pos] = v;
                                            trace_log(&logger, local_buf, &local_len, &local_count,
                                                      "WRITE", &next_frontier[pos], "next_frontier", pos);
                                        }
                                    }
                                }
                            }
                            trace_flush(&logger, local_buf, &local_len, &local_count);
                        }"""

new_task = """                        #pragma omp task firstprivate(start, end)
                        {
                            int tid = omp_get_thread_num();
                            char local_buf[TRACE_BUF_SIZE];
                            size_t local_len = 0;
                            uint64_t local_count = 0;

                            for (size_t idx = start; idx < end; idx++) {
                                trace_log(&logger, local_buf, &local_len, &local_count,
                                          tid, "READ", &frontier[idx], "frontier", idx);
                                node_t u = frontier[idx];

                                trace_log(&logger, local_buf, &local_len, &local_count,
                                          tid, "READ", &graph->row_pointers[u], "row_pointers", u);
                                edge_t start_edge = graph->row_pointers[u];

                                trace_log(&logger, local_buf, &local_len, &local_count,
                                          tid, "READ", &graph->row_pointers[u + 1], "row_pointers", u + 1);
                                edge_t end_edge = graph->row_pointers[u + 1];

                                for (edge_t e = start_edge; e < end_edge; e++) {
                                    trace_log(&logger, local_buf, &local_len, &local_count,
                                              tid, "READ", &graph->column_indices[e], "column_indices", e);
                                    node_t v = graph->column_indices[e];

                                    trace_log(&logger, local_buf, &local_len, &local_count,
                                              tid, "READ", &distances[v], "distances", v);
                                    if (distances[v] == -1) {
                                        if (__sync_bool_compare_and_swap(&distances[v], -1, current_level + 1)) {
                                            trace_log(&logger, local_buf, &local_len, &local_count,
                                                      tid, "WRITE", &distances[v], "distances", v);
                                            size_t pos = __sync_fetch_and_add(&next_size, 1);
                                            next_frontier[pos] = v;
                                            trace_log(&logger, local_buf, &local_len, &local_count,
                                                      tid, "WRITE", &next_frontier[pos], "next_frontier", pos);
                                        }
                                    }
                                }
                            }
                            trace_flush(&logger, local_buf, &local_len, &local_count);
                        }"""

is_crlf = '\r\n' in content
c_norm = content.replace('\r\n', '\n')

assert old_trace_log in c_norm, "old_trace_log not found"
assert old_root in c_norm, "old_root not found"
assert old_task in c_norm, "old_task not found"

c_norm = c_norm.replace(old_trace_log, new_trace_log)
c_norm = c_norm.replace(old_root, new_root)
c_norm = c_norm.replace(old_task, new_task)

c_final = c_norm.replace('\n', '\r\n') if is_crlf else c_norm

with open(path, 'w', encoding='utf-8') as f:
    f.write(c_final)

print("Patch applied successfully!")

