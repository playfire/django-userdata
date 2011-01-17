from django.db import models, IntegrityError, transaction
from django.db.models.signals import post_save, pre_delete
from django.contrib.auth.models import User

INSTANCES = []

def PerUserData(related_name=None):
    """
    Class factory that returns an abstract model attached to a ``User`` object
    that creates and destroys concrete child instances where required.

    Example usage::

        class ToppingPreferences(PerUserData('toppings')):
            pepperoni = models.BooleanField(default=True)
            anchovies = models.BooleanField(default=False)

        >>> u = User.objects.create_user('test', 'example@example.com')
        >>> u.toppings  # ToppingPreferences created automatically
        <ToppingPreferences: user=test>
        >>> u.toppings.anchovies
        False

    You can specify dynamic defaults and perform post-creation setup using the
    ``setup`` and ``get_defaults`` methods::

        class ToppingPreferences(PerUserData('toppings')):
            pepperoni = models.BooleanField(default=True)
            anchovies = models.BooleanField(default=False)

            def setup(self):
                self.pepperoni = False
                self.save()

            @classmethod
            def get_defaults(self, user):
                return {'anchovies': True}


        >>> u = User.objects.create_user('test', 'example@example.com')
        >>> u.toppings.anchovies
        True
        >>> u.toppings.pepperoni
        False

    These methods could not be folded into the ``save()`` as this method cannot
    tell whether it has just been created or not (as it always has a primary
    key).
    """

    class UserDataBase(models.base.ModelBase):
        def __new__(cls, name, bases, attrs):
            model = super(UserDataBase, cls).__new__(cls, name, bases, attrs)

            if model._meta.abstract:
                return model

            def on_create(sender, instance, created, *args, **kwargs):
                if not created:
                    return
                try:
                    data = {'user': instance}
                    data.update(model.get_defaults(instance))
                    obj = model.objects.create(**data)
                    obj.setup()
                except:
                    print "Error when creating PerUserData %r" % model
                    raise

            def on_delete(sender, instance, *args, **kwargs):
                model.objects.filter(pk=instance).delete()

            post_save.connect(on_create, sender=User, weak=False)
            pre_delete.connect(on_delete, sender=User, weak=False)

            INSTANCES.append(model)

            return model

    class UserData(models.Model):
        user = models.OneToOneField(
            'auth.User',
            primary_key=True,
            related_name=related_name,
        )

        __metaclass__ = UserDataBase

        class Meta:
            abstract = True

        def __unicode__(self):
            return 'user=%s' % self.user.username

        def setup(self):
            pass

        @classmethod
        def get_defaults(cls, user):
            return {}

        @classmethod
        @transaction.commit_on_success
        def for_user(cls, user, **kwargs):
            try:
                obj, created = cls.get_or_create(user)
            except IntegrityError, e:
                # commit() ensures our view of the db is up-to-date, which is not
                # always the case after an integrity error
                transaction.commit()
                try:
                    obj = cls.objects.get(user=user)
                except cls.DoesNotExist:
                    raise e
            return obj

        @classmethod
        def get_or_create(cls, user):
            return cls.objects.get_or_create(user=user)

    return UserData

def lint():
    for model in INSTANCES:
        qs = User.objects.filter(**{
            '%s__pk__isnull' % model.user.field.related_query_name(): True,
        })

        if not qs.exists():
            continue

        print "W: %d users are missing %s instances: %r" % (len(qs), model, qs)
