//Direct tag access instead of 'id'
const faqCard = document.querySelectorAll('.FAQ-card') 
const mobileNav = document.querySelectorAll('.mobile-header-wrapper')

//Use classList to add, remove, or toggle a class on the element.
faqCard.forEach(item => {
    item.addEventListener('click', () => {
        item.classList.toggle('active');
    })
})

mobileNav.forEach(item => {
    item.addEventListener('click', () => {
        item.classList.toggle('active');
    })
})