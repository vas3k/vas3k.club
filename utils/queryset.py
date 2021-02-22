def chunked_queryset(queryset, chunk_size=1000):
    start_pk = 0
    queryset = queryset.order_by("pk")

    while True:
        # no entries left
        if not queryset.filter(pk__gt=start_pk).exists():
            break

        try:
            # fetch chunk_size entries
            end_pk = queryset.filter(pk__gt=start_pk).values_list("pk", flat=True)[chunk_size - 1]
        except IndexError:
            # fetch rest entries if less than chunk_size left
            end_pk = queryset.values_list("pk", flat=True).last()

        yield queryset.filter(pk__gt=start_pk).filter(pk__lte=end_pk)

        start_pk = end_pk
