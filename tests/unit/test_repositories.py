from app.models.application import ApplicationStatus
from app.models.offer import OfferStatus
from app.models.role import RoleEnum
from app.repositories.application_repository import ApplicationRepository
from app.repositories.offer_repository import OfferRepository
from app.repositories.user_repository import UserRepository
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.schemas.auth import UserCreate
from app.schemas.offer import OfferCreate, OfferUpdate
from app.utils.hashing import hash_password
from app.utils.time import utcnow


async def test_base_repository_update_with_no_fields_is_a_no_op(db_session):
    users = UserRepository(db_session)
    offers = OfferRepository(db_session)
    company = await users.create(
        UserCreate(
            username="acme",
            email="co@x.com",
            hashed_password=hash_password("pw"),
            full_name="ACME",
            role=RoleEnum.company,
        )
    )
    offer = await offers.create(OfferCreate(company_id=company.id, title="t", mission="m", skills="s"))

    unchanged = await offers.update(offer.id, OfferUpdate())
    assert unchanged.title == "t"
    assert unchanged.status == OfferStatus.draft


async def test_user_repository_lookup(db_session):
    repo = UserRepository(db_session)
    user = await repo.create(
        UserCreate(
            username="ada",
            email="a@b.com",
            hashed_password=hash_password("pw"),
            full_name="A",
            role=RoleEnum.student,
        )
    )
    await db_session.commit()

    assert (await repo.get_by_email("a@b.com")).id == user.id
    assert await repo.get_by_email("missing@b.com") is None
    assert (await repo.get_by_username("ada")).id == user.id
    assert (await repo.get(user.id)).id == user.id


async def test_offer_repository_filters_and_counts(db_session):
    users = UserRepository(db_session)
    offers = OfferRepository(db_session)
    company = await users.create(
        UserCreate(
            username="acme",
            email="co@x.com",
            hashed_password=hash_password("pw"),
            full_name="ACME",
            role=RoleEnum.company,
        )
    )

    published = await offers.create(
        OfferCreate(company_id=company.id, title="t", mission="m", skills="s")
    )
    draft = await offers.create(
        OfferCreate(company_id=company.id, title=None, mission=None, skills=None)
    )
    published = await offers.update(
        published.id, OfferUpdate(status=OfferStatus.published, updated_at=utcnow())
    )
    await db_session.commit()

    assert [o.id for o in await offers.list_published()] == [published.id]
    assert {o.id for o in await offers.list_by_company(company.id)} == {
        published.id,
        draft.id,
    }
    assert set(o.id for o in await offers.get_all()) == {published.id, draft.id}
    assert await offers.count_by_status() == {"published": 1, "draft": 1}


async def test_application_repository_active_flag_ignores_rejected(db_session):
    users = UserRepository(db_session)
    offers = OfferRepository(db_session)
    applications = ApplicationRepository(db_session)

    company = await users.create(
        UserCreate(
            username="acme",
            email="co@x.com",
            hashed_password=hash_password("pw"),
            full_name="ACME",
            role=RoleEnum.company,
        )
    )
    student = await users.create(
        UserCreate(
            username="ada",
            email="stu@x.com",
            hashed_password=hash_password("pw"),
            full_name="Ada",
            role=RoleEnum.student,
        )
    )
    offer = await offers.create(
        OfferCreate(company_id=company.id, title="t", mission="m", skills="s")
    )
    await db_session.flush()

    assert (
        await applications.has_active_application(offer_id=offer.id, student_id=student.id)
        is False
    )

    application = await applications.create(
        ApplicationCreate(offer_id=offer.id, student_id=student.id)
    )
    assert (
        await applications.has_active_application(offer_id=offer.id, student_id=student.id)
        is True
    )

    application = await applications.update(
        application.id, ApplicationUpdate(status=ApplicationStatus.rejected, updated_at=utcnow())
    )
    assert (
        await applications.has_active_application(offer_id=offer.id, student_id=student.id)
        is False
    )

    deleted = await applications.delete(application.id)
    assert deleted is True
    assert await applications.get(application.id) is None
