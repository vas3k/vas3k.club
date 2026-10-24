from godmode.admin import ClubAdminModel
from posts.models.post import Post


class PostAdminModel(ClubAdminModel):
    def save_model(self, request, form):
        post = form.save(commit=False)

        if (
            post.moderation_status != form.initial.get("moderation_status")
            and post.moderation_status in {
                Post.MODERATION_APPROVED,
                Post.MODERATION_FORGIVEN,
                Post.MODERATION_REJECTED,
            }
        ):
            if post.moderation_status == Post.MODERATION_REJECTED:
                data = post.moderation_data or {}
                post.record_moderator_decision(request.me, reason=data.get("reason"), text=data.get("text"))
            else:
                post.record_moderator_decision(request.me)

        post.save()
        form.save_m2m()
        return post
